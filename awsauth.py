import base64
import hmac
import urllib
from hashlib import sha1 as sha
from urlparse import urlparse
from email.utils import formatdate
from requests.auth import AuthBase

class S3Auth(AuthBase):
    # List of Query String Arguments of Interest
    special_params = ['acl', 'location', 'logging', 'partNumber', 'policy',
                       'requestPayment', 'torrent', 'versioning', 'versionId',
                       'versions', 'website', 'uploads', 'uploadId',
                       'response-content-type', 'response-content-language',
                       'response-expires', 'reponse-cache-control',
                       'response-content-disposition',
                       'response-content-encoding']


    """Attaches AWS Authentication to the given Request object."""
    def __init__(self, access_key, secret_key):
        self.access_key = str(access_key)
        self.secret_key = str(secret_key)

    def __call__(self, r):
        #Create date header if it is not created yet
        if not r.headers.has_key('date') and not r.headers.has_key('x-amz-date'):
            r.headers['date'] = formatdate(timeval=None, localtime=False, usegmt=True)
        r.headers['Authorization'] = 'AWS %s:%s'%(self.access_key, self.get_signature(r))
        return r

    def get_signature(self, r):   
        h = hmac.new(self.secret_key, self.get_canonical_string(r), digestmod=sha)
        return base64.encodestring(h.digest()).strip()

    def get_canonical_string(self, r):
        parsedurl = urlparse(r.url)
        objectkey = parsedurl.path[1:]
        query_args = parsedurl.query.split('&')
        #Sort alphabetical
        query_args.sort()
        bucket = ''
        if len(parsedurl.netloc.split('.')) == 4:
            bucket = parsedurl.netloc.split('.')[0]
        if len(parsedurl.netloc.split('.')) == 3 and parsedurl.netloc.split('.')[0].lower() != 's3':
            bucket = parsedurl.netloc.split('.')[0]
        
        interesting_headers = {}
        for key in r.headers:
            lk = key.lower()
            if r.headers[key] != None and (lk in ['content-md5', 'content-type', 'date'] or
                                         lk.startswith('x-amz-')):
                interesting_headers[lk] = r.headers[key].strip()
    
        # these keys get empty strings if they don't exist
        if not interesting_headers.has_key('content-type'):
            interesting_headers['content-type'] = ''
        if not interesting_headers.has_key('content-md5'):
            interesting_headers['content-md5'] = ''
    
        # If x-amz-date is used it supersedes the date header.
        if interesting_headers.has_key('x-amz-date'):
            interesting_headers['date'] = ''
                    
        sorted_header_keys = interesting_headers.keys()
        sorted_header_keys.sort()
    
        buf = "%s\n" % r.method
        for key in sorted_header_keys:
            val = interesting_headers[key]
            if key.startswith('x-amz-'):
                buf += "%s:%s\n" % (key, val)
            else:
                buf += "%s\n" % val
    
        # append the bucket if it exists
        if bucket != "":
            buf += "/%s" % bucket
    
        # add the objectkey.  even if it doesn't exist, add the slash
        buf += "/%s" % urllib.quote_plus(objectkey)
    
        params_found = False
        # handle special query string arguments
        for q in query_args:
            k = q.split('=')[0]
            if k in self.special_params:
                if params_found:
                    buf += "&%s"%q
                else:    
                    buf += "?%s"%q
                params_found = True              
        return buf       
