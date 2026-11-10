#!/usr/bin/env python3
"""
UBG Ultra — Lightweight Dynamic Proxy
Ultraviolet-style URL rewriting proxy in pure Python stdlib.

Usage (from an http.server handler):
    Proxy.install(handler_class, prefix="/proxy/")
or call Proxy.handle(handler) inside do_GET/do_POST.

Rewrites HTML/CSS so relative and absolute assets are pulled through the
proxy, strips CSP / X-Frame-Options so pages embed in the player iframe,
and sets no-referrer so nothing leaks back to the origin site.
"""

import base64
import io
import re
import threading
import urllib.request
import urllib.error
import urllib.parse
import socket
from html.parser import HTMLParser

TIMEOUT = 25
MAX_BODY = 64 * 1024 * 1024          # 64 MB upstream cap
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/124.0.0.0 Safari/537.36")

# Tiny in-memory cookie jar keyed by host, so session-based sites work.
COOKIE_JAR = {}
COOKIE_LOCK = threading.Lock()

# Small in-memory cache for GET responses (speeds up repeat loads a lot).
CACHE = {}
CACHE_MAX = 128
CACHE_TTL = 60                     # seconds


def _cache_get(key):
    if not key:
        return None
    item = CACHE.get(key)
    if not item:
        return None
    if item[0] < __import__("time").time():
        CACHE.pop(key, None)
        return None
    return item


def _cache_put(key, value):
    if len(CACHE) >= CACHE_MAX:
        for k in list(CACHE)[: len(CACHE) - CACHE_MAX + 8]:
            CACHE.pop(k, None)
    CACHE[key] = value


def _cache_clear():
    CACHE.clear()

_TEXT_TYPES = ("text/", "application/javascript", "application/json",
               "application/xml", "application/xhtml+xml")
_HTML_TYPES = ("text/html", "application/xhtml+xml")
_CSS_TYPES = ("text/css",)
_STRIP_HEADERS = (
    "x-frame-options", "content-security-policy", "content-security-policy-report-only",
    "referrer-policy", "strict-transport-security", "public-key-pins",
    "cross-origin-opener-policy", "cross-origin-embedder-policy",
    "x-content-type-options",
)
_URL_ATTRS = (
    "href", "src", "srcset", "action", "poster", "data-src", "data", "srcset",
    "data-href", "data-srcset", "data-original", "data-lazy-src",
)

# Injected early into proxied <head> (before any site script runs): routes
# fetch()/XHR/EventSource/window.open/location changes/relative URLs through
# the proxy, rewrites dynamically-added nodes and anchors/forms, so SPA-style
# and fetch-heavy sites actually load fully (CroxyProxy-style behaviour).
_PATCHER = """<script>
(function(){
var P="/proxy/";
function b64u(s){return btoa(unescape(encodeURIComponent(s))).replace(/\\+/g,"-").replace(/\\//g,"_").replace(/=+$/,"");}
function originOf(){var parts=location.pathname.split("/").filter(Boolean),e;if(parts.length){e=parts[parts.length-1].replace(/-/g,"+").replace(/_/g,"/");while(e.length%4)e+="=";try{var r=atob(e);return decodeURIComponent(escape(r));}catch(_){}}return location.href;}
var base=originOf();
function resolve(ref){ref=(ref||"").trim();if(!ref||ref.charAt(0)==="#")return ref;if(/^https?:\\/\\//i.test(ref))return ref;if(/^[a-z][a-z0-9+.\\-]*:/i.test(ref))return ref;var u;if(ref.indexOf("//")===0){u=base.split(":")[0]+":"+ref;}else if(ref.charAt(0)==="/"){u=base.split("/").slice(0,3).join("/")+ref;}else{u=base.slice(0,base.lastIndexOf("/")+1)+ref;}var parts=u.split("/"),out=[];for(var i=0;i<parts.length;i++){var p=parts[i];if(p===".")continue;if(p===".."){if(out.length>3)out.pop();continue;}out.push(p);}return out.join("/");}
function prox(ref){var a=resolve(ref);if(!/^https?:\\/\\//i.test(a))return a;return P+b64u(a);}
function isProxy(u){return typeof u==="string"&&u.indexOf("/proxy/")===0;}
function URLATTRS(){return ["src","href","data-src","data-href","data-original","data-lazy-src","poster","action"];}
function fixNode(n){if(!n||n.nodeType!==1)return;var at=URLATTRS();for(var i=0;i<at.length;i++){var v=n.getAttribute(at[i]);if(v&&!isProxy(v)){try{n.setAttribute(at[i],prox(v));}catch(_){}}}var list=n.querySelectorAll?n.querySelectorAll("["+at.join("], [")+"]"):[];for(var k=0;k<list.length;k++){var el=list[k];for(var j=0;j<at.length;j++){var av=el.getAttribute(at[j]);if(av&&!isProxy(av)){try{el.setAttribute(at[j],prox(av));}catch(_){}}}}}
function hook(){
if(window.__ubgP)return;window.__ubgP=true;
var f=window.fetch;if(f){window.fetch=function(i,o){if(typeof i==="string"&&!isProxy(i))i=prox(i);return f.call(this,i,o);};}
var X=window.XMLHttpRequest;if(X){var op=X.prototype.open;X.prototype.open=function(m,u){if(typeof u==="string"&&!isProxy(u))u=prox(u);return op.apply(this,arguments);};}
var O=window.open;if(O){window.open=function(u){if(typeof u==="string"&&!isProxy(u))u=prox(u);return O.apply(this,arguments);};}
var ES=window.EventSource;if(ES){window.EventSource=function(u,c){if(typeof u==="string"&&!isProxy(u))u=prox(u);return new ES(u,c);};try{window.EventSource.prototype=ES.prototype;window.EventSource.CONNECTING=ES.CONNECTING;window.EventSource.OPEN=ES.OPEN;window.EventSource.CLOSED=ES.CLOSED;}catch(_){}}
if(navigator&&navigator.serviceWorker){try{navigator.serviceWorker.register=function(){return Promise.reject(new Error("disabled by proxy"));};navigator.serviceWorker.getRegistrations=function(){return Promise.resolve([]);};}catch(_){}}
try{var hd=Object.getOwnPropertyDescriptor(window.location,"href");if(hd&&hd.set&&!window.__ubgSpa){Object.defineProperty(window.location,"href",{configurable:true,get:function(){try{return hd.get.call(window.location);}catch(_){return location.href;}},set:function(v){try{hd.set.call(window.location,typeof v==="string"&&!isProxy(v)?prox(v):v);}catch(_){location.assign(typeof v==="string"&&!isProxy(v)?prox(v):v);}}});}}catch(_){}
if(window.location.assign){var _la=window.location.assign;window.location.assign=function(v){if(typeof v==="string"&&!isProxy(v))v=prox(v);return _la.call(window.location,v);};}
if(window.location.replace){var _lr=window.location.replace;window.location.replace=function(v){if(typeof v==="string"&&!isProxy(v))v=prox(v);return _lr.call(window.location,v);};}
var SA=Element.prototype.setAttribute;Element.prototype.setAttribute=function(a,v){if(typeof a==="string"&&typeof v==="string"&&URLATTRS().indexOf(a.toLowerCase())>=0&&!isProxy(v)){try{v=prox(v);}catch(_){}}return SA.call(this,a,v);};
document.addEventListener("click",function(e){var t=e.target;while(t&&t!==document){if(t.nodeType===1&&t.getAttribute){var u=t.getAttribute("href");if(u&&!isProxy(u)&&/^https?:\\/\\//i.test(resolve(u))){t.setAttribute("href",prox(u));}else if(u&&u.indexOf("//")===0&&!isProxy(u)){t.setAttribute("href",prox(u));}}t=t.parentNode;}},true);
document.addEventListener("submit",function(e){var fm=e.target;if(fm&&fm.getAttribute){var u=fm.getAttribute("action");if(u&&!isProxy(u)&&(/^https?:\\/\\//i.test(resolve(u))||u.indexOf("//")===0)){fm.setAttribute("action",prox(u));}}},true);
if(window.MutationObserver){try{new MutationObserver(function(muts){for(var i=0;i<muts.length;i++){var m=muts[i];for(var j=0;j<m.addedNodes.length;j++)fixNode(m.addedNodes[j]);if(m.type==="attributes"&&m.attributeName){var el=m.target;if(el&&el.nodeType===1&&URLATTRS().indexOf(m.attributeName.toLowerCase())>=0){var v=el.getAttribute(m.attributeName);if(v&&!isProxy(v)){try{el.setAttribute(m.attributeName,prox(v));}catch(_){}}}}}}).observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:["src","href","data-src","data-href","data-original","data-lazy-src","poster","action"]});}catch(_){}}
}
if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",hook);}else{hook();}})();
/* ---- SPA path shim: present the ORIGINAL site URL to client-side
   routers (React/Vue) so /proxy/<b64> is never seen as the route, and
   translate history.pushState / dynamic element src back into the proxy. */
(function(){
if(window.__ubgSpa)return;window.__ubgSpa=true;
try{
var P="/proxy/";
function b64u(s){return btoa(unescape(encodeURIComponent(s))).replace(/\+/g,"-").replace(/\//g,"_").replace(/=+$/,"");}
function deb64u(s){s=s.replace(/-/g,"+").replace(/_/g,"/");while(s.length%4)s+="=";return decodeURIComponent(escape(atob(s)));}
function curBase(){var parts=location.pathname.split("/").filter(Boolean),e;if(parts.length){e=parts[parts.length-1];try{return deb64u(e);}catch(_){}}return location.href;}
var cur=null;try{cur=new URL(curBase());}catch(_){}
function origin(){return cur?cur.origin:location.origin;}
function isProxy(u){return typeof u==="string"&&u.indexOf("/proxy/")===0;}
function toProxy(u){var a;if(/^https?:\/\//i.test(u)){a=u;}else if(u.charAt(0)==="/"){a=origin()+u;}else{a=origin()+"/"+u;}return P+b64u(a);}
function fromProxyPath(p){var e=p.slice(P.length).replace(/-/g,"+").replace(/_/g,"/");while(e.length%4)e+="=";return decodeURIComponent(escape(atob(e)));}
function syncCur(){try{var p=location.pathname;if(isProxy(p)){cur=new URL(fromProxyPath(p));}}catch(_){}}
function applyArg(u){try{if(typeof u==="string"&&u&&!isProxy(u)){cur=new URL(u.charAt(0)==="/"?origin()+u:u);}}catch(_){}}
function define(n,get,set){try{Object.defineProperty(window.location,n,{configurable:true,get:function(){return get();},set:function(v){set(v);}});}catch(_){}}
if(cur){
  define("pathname",function(){return cur.pathname;},function(v){location.assign(toProxy(v));});
  define("search",function(){return cur.search;},function(v){location.assign(toProxy(cur.pathname+v));});
  define("hash",function(){return cur.hash;},function(v){location.assign(toProxy(cur.pathname+cur.search+v));});
  define("href",function(){return cur.href;},function(v){location.assign(typeof v==="string"&&!isProxy(v)?toProxy(v):v);});
  define("protocol",function(){return cur.protocol;},function(){});
  define("host",function(){return cur.host;},function(){});
  define("hostname",function(){return cur.hostname;},function(){});
  define("port",function(){return cur.port;},function(){});
  define("origin",function(){return cur.origin;},function(){});
}
if(window.history){
  var hp=window.history.pushState,hr=window.history.replaceState;
  if(hp){window.history.pushState=function(st,t,u){if(typeof u==="string"&&u&&!isProxy(u)){applyArg(u);u=toProxy(u);}return hp.apply(this,arguments);};}
  if(hr){window.history.replaceState=function(st,t,u){if(typeof u==="string"&&u&&!isProxy(u)){applyArg(u);u=toProxy(u);}return hr.apply(this,arguments);};}
  window.addEventListener("popstate",syncCur);
}
var SRCS=["HTMLScriptElement","HTMLImageElement","HTMLIFrameElement","HTMLVideoElement","HTMLAudioElement","HTMLSourceElement","HTMLLinkElement"];
for(var i=0;i<SRCS.length;i++){
  var T=window[SRCS[i]];if(!T||!T.prototype)continue;
  var d=Object.getOwnPropertyDescriptor(T.prototype,"src");if(!d||!d.set)continue;
  (function(ds){Object.defineProperty(T.prototype,"src",{configurable:true,get:ds.get,set:function(v){try{if(typeof v==="string"&&v&&!isProxy(v)){var a=/^https?:\/\//i.test(v)?v:origin()+((v.charAt(0)==="/")?v:"/"+v);if(!isProxy(a))v=P+b64u(a);}}catch(_){}return ds.set.call(this,v);}});})(d);
}
}catch(_){}
})();
</script>"""
_FRAME_BUSTERS = (
    (re.compile(r'if\s*\(\s*(?:top|parent|self)\s*[!===]+\s*(?:self|top)\s*\)', re.I), "if (false)"),
    (re.compile(r'window\.top\.location', re.I), "window.location"),
    (re.compile(r'top\.location\.(?:href\s*=|replace\()', re.I), "location."),
    (re.compile(r'parent\.location\.(?:href\s*=|replace\()', re.I), "location."),
    (re.compile(r'if\s*\(.*top\s*!=+\s*self.*\)\s*\{?\s*', re.I), ""),
)


def _b64_encode(url: str) -> str:
    raw = url.encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64_decode(encoded: str) -> str:
    pad = "=" * (-len(encoded) % 4)
    return base64.urlsafe_b64decode((encoded + pad).encode("ascii")).decode("utf-8")


def _resolve(base: str, ref: str) -> str:
    return urllib.parse.urljoin(base, ref.strip())


def _is_proxyable(url: str) -> bool:
    return url.lower().startswith(("http://", "https://"))


def _rewrite_css(css: str, base: str) -> str:
    def repl(m):
        quote, ref = m.group(1), m.group(2)
        absu = _resolve(base, ref)
        if not _is_proxyable(absu):
            return m.group(0)
        return "url(%s/proxy/%s%s)" % (quote, _b64_encode(absu), quote)

    css = re.sub(r"url\(\s*(['\"]?)([^'\")\s]+)(['\"]?)\s*\)", repl, css)
    css = re.sub(
        r"(@import\s+)(['\"])(.*?)(\2)",
        lambda m: "%s%s/proxy/%s%s" % (
            m.group(1), m.group(2), _b64_encode(_resolve(base, m.group(3))), m.group(2)),
        css, flags=re.I)
    return css


def _rewrite_html(html: str, base: str) -> str:
    # Frame-busting removal (best effort)
    for rx, repl in _FRAME_BUSTERS:
        html = rx.sub(repl, html)
    # <base> would hijack our root-relative /proxy/ URLs — drop it entirely.
    html = re.sub(r"<base[^>]*>", "", html, flags=re.I)
    # Inline <style> blocks
    def style_block(m):
        return "<style" + m.group(1) + ">" + _rewrite_css(m.group(2), base) + "</style>"
    html = re.sub(r"<style([^>]*)>(.*?)</style>", style_block, html, flags=re.I | re.S)
    # CSS url() in style="..." attributes
    def style_attr(m):
        return m.group(1) + _rewrite_css(m.group(2), base) + m.group(3)
    html = re.sub(r'(\sstyle=")(.*?)(")', style_attr, html, flags=re.I | re.S)
    html = re.sub(r"(\sstyle=')(.*?)(')", style_attr, html, flags=re.I | re.S)
    # URL-bearing attributes
    for attr in _URL_ATTRS:
        html = re.sub(
            r"(" + re.escape(attr) + r")\s*=\s*([\"'])(.*?)(\2)",
            lambda m, a=attr: _attr_repl(m, a, base),
            html, flags=re.I | re.S,
        )
    # <meta http-equiv=refresh content="0; url=...">
    def meta_refresh(m):
        prefix, quote, rest = m.group(1), m.group(2), m.group(3)
        match = re.search(r"(url\s*=\s*)([\"']?)(.*?)([\"']?)$", rest, re.I)
        if not match:
            return m.group(0)
        absu = _resolve(base, match.group(3))
        return (prefix + quote + match.group(0)[:match.start()] +
                match.group(1) + match.group(2) + "/proxy/" + _b64_encode(absu) + match.group(4) + quote)
    html = re.sub(
        r'(<meta[^>]+http-equiv\s*=\s*["\']?refresh["\']?[^>]*content\s*=\s*)(["\'])(.*?)(\2)',
        meta_refresh, html, flags=re.I | re.S,
    )
    # Inject no-referrer meta right after <head>
    if re.search(r"<head[^>]*>", html, re.I):
        html = re.sub(r"(<head[^>]*>)", r"\1<meta name=\"referrer\" content=\"no-referrer\">",
                      html, count=1, flags=re.I)
    else:
        html = '<meta name="referrer" content="no-referrer">' + html
    # Inject the client-side URL patcher EARLY (right after <head>) so it runs
    # before any of the site's own inline scripts and can catch their fetches.
    if re.search(r"<head[^>]*>", html, re.I):
        html = re.sub(r"(<head[^>]*>)", r"\1" + _PATCHER,
                      html, count=1, flags=re.I)
    else:
        html = _PATCHER + html
    return html


def _attr_repl(m, attr, base):
    quote, ref = m.group(2), m.group(3)
    if attr in ("srcset", "data-srcset"):
        parts = []
        for chunk in ref.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            tokens = chunk.split()
            if tokens:
                absu = _resolve(base, tokens[0])
                tokens[0] = "/proxy/" + _b64_encode(absu)
            parts.append(" ".join(tokens))
        return attr + "=" + quote + ", ".join(parts) + quote
    if ref.lstrip().startswith("#"):
        return attr + "=" + quote + ref + quote
    if not _is_proxyable(_resolve(base, ref)):
        return attr + "=" + quote + ref + quote
    absu = _resolve(base, ref)
    return attr + "=" + quote + "/proxy/" + _b64_encode(absu) + quote


class _PageParser(HTMLParser):
    """Finds the <title> tag for error reporting (unused but handy)."""
    def __init__(self):
        super().__init__()
        self.title = None
        self._in = False

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in = True

    def handle_data(self, data):
        if self._in:
            self.title = (self.title or "") + data

    def handle_endtag(self, tag):
        if tag == "title":
            self._in = False


def fetch(url: str, method: str = "GET", body: bytes = None, headers: dict = None):
    host = urllib.parse.urlsplit(url).netloc.lower()
    req_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "identity",
        "Referer": "",  # no referrer leak
    }
    with COOKIE_LOCK:
        jar = COOKIE_JAR.get(host)
    if jar:
        req_headers["Cookie"] = "; ".join("%s=%s" % (k, v) for k, v in jar.items())
    if headers:
        req_headers.update({k: v for k, v in headers.items()
                            if k.lower() not in ("host", "referer", "connection",
                                                 "content-length", "accept-encoding", "cookie")})
    data = body if method.upper() in ("POST", "PUT", "PATCH") else None
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method.upper())
    try:
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
    except urllib.error.HTTPError as e:
        resp = e
    # Remember Set-Cookie from the response for future requests to this host.
    _jar_remember(host, resp.headers)
    final = resp.geturl()
    if final and urllib.parse.urlsplit(final).netloc.lower() != host:
        _jar_remember(urllib.parse.urlsplit(final).netloc.lower(), resp.headers)
    return resp


def _jar_remember(host, headers):
    cookies = {}
    try:
        items = headers.items() if hasattr(headers, "items") else []
    except Exception:
        return
    for k, v in items:
        if str(k).lower() != "set-cookie":
            continue
        name, _, val = str(v).partition("=")
        if not name.strip():
            continue
        cookies[name.strip()] = val.split(";")[0].strip()
    if not cookies:
        return
    with COOKIE_LOCK:
        cur = COOKIE_JAR.setdefault(host, {})
        cur.update(cookies)


def handle(handler, prefix="/proxy/"):
    """Handle a request whose path starts with prefix."""
    path = handler.path
    if path.startswith(prefix):
        encoded = path[len(prefix):].split("?")[0]
    else:
        # /proxy/<b64>/?<query> — keep query in the target URL
        encoded = path[len(prefix):]
    if not encoded:
        _json(handler, 400, {"error": "Missing URL. Use /proxy/<base64url>"})
        return

    try:
        target = _b64_decode(encoded)
    except Exception:
        _json(handler, 400, {"error": "Invalid proxy URL encoding."})
        return
    if not _is_proxyable(target):
        _json(handler, 400, {"error": "Only http/https URLs are supported."})
        return

    method = handler.command
    body = None
    if method in ("POST", "PUT", "PATCH"):
        length = int(handler.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            _json(handler, 413, {"error": "Request body too large."})
            return
        body = handler.rfile.read(length) if length else b""

    # Serve from cache for repeat GETs (much faster on reloads).
    cache_key = target if method == "GET" else None
    cached = _cache_get(cache_key) if cache_key else None
    if cached:
        _, raw, ctype, resp_status = cached
        final_url = target
        handler.send_response(resp_status)
        handler.send_header("Content-Type", ctype)
        handler.send_header("Content-Length", str(len(raw)))
        handler.send_header("Referrer-Policy", "no-referrer")
        handler.send_header("X-Frame-Options", "SAMEORIGIN")
        handler.end_headers()
        try:
            handler.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            pass
        return

    try:
        resp = fetch(target, method, body, dict(handler.headers))
    except (urllib.error.URLError, socket.timeout, OSError, ValueError) as e:
        _json(handler, 502, {"error": "Upstream fetch failed: %s" % str(e)})
        return

    ctype = (resp.headers.get("Content-Type") or "application/octet-stream").split(";")[0].strip().lower()
    final_url = resp.geturl()
    raw = resp.read()

    # Defense in depth: decompress if the upstream ignored our identity request.
    cenc = (resp.headers.get("Content-Encoding") or "").strip().lower()
    if cenc in ("gzip", "x-gzip"):
        try:
            raw = __import__("gzip").decompress(raw)
        except Exception:
            pass
    elif cenc == "deflate":
        try:
            raw = __import__("zlib").decompress(raw)
        except Exception:
            try:
                raw = __import__("zlib").decompress(raw, -15)
            except Exception:
                pass

    if ctype in _HTML_TYPES:
        try:
            text = raw.decode("utf-8", errors="replace")
            out = _rewrite_html(text, final_url)
            raw = out.encode("utf-8")
        except Exception:
            pass
    elif ctype in _CSS_TYPES:
        try:
            text = raw.decode("utf-8", errors="replace")
            raw = _rewrite_css(text, final_url).encode("utf-8")
        except Exception:
            pass

    if cache_key:
        import time as _t
        _cache_put(cache_key, (_t.time() + CACHE_TTL, raw, ctype, resp.status))

    handler.send_response(resp.status)
    safe_headers = [(k, v) for k, v in resp.headers.items() if k.lower() not in _STRIP_HEADERS]
    sent = set()
    for k, v in safe_headers:
        kl = k.lower()
        if kl in sent or kl in ("transfer-encoding", "content-length", "content-encoding",
                                "connection", "keep-alive", "date", "server"):
            continue
        handler.send_header(k, v)
        sent.add(kl)
    handler.send_header("Content-Length", str(len(raw)))
    handler.send_header("Referrer-Policy", "no-referrer")
    handler.send_header("X-Frame-Options", "SAMEORIGIN")
    handler.end_headers()
    try:
        handler.wfile.write(raw)
    except (BrokenPipeError, ConnectionResetError):
        pass


def _json(handler, status, payload):
    data = __import__("json").dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Referrer-Policy", "no-referrer")
    handler.end_headers()
    handler.wfile.write(data)
