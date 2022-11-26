class Cookie:
    def __init__(self, name, value, expires, path, http_only, secure, session_only, same_site):
        self.name = name
        self.value = value
        self.expires = expires
        self.path = path
        self.http_only = http_only
        self.secure = secure
        self.session_only = session_only
        self.same_site = same_site

        cookie = Cookie.SimpleCookie()
        cookie[cookie_name] = cookie_value
        cookie[cookie_name]['path'] = '/'

    def __repr__(self):
        http_only = '\nHttpOnly' if self.http_only else ''
        session = '\nSession' if self.session_only else ''
        same_site = '\nSameSite: ' + self.same_site if self.same_site else ''

        return 'Name: {name}\nValue: {value}\nExpiration date: {expires}\nPath: {path}{http_only}{session}{same_site}'.format(
                name=self.name, value=self.value, expires=self.expires,
                path=self.path, http_only=http_only, session=session, same_site=same_site)