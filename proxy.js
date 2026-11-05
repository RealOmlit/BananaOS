import fetch from 'node-fetch';

export async function handleProxy(req, res) {
  const targetUrl = req.query.url;

  if (!targetUrl) {
    return res.status(400).send('Missing "url" query parameter.');
  }

  let parsedUrl;
  try {
    parsedUrl = new URL(targetUrl);
  } catch (err) {
    return res.status(400).send('Invalid URL format.');
  }

  try {
    const upstreamResponse = await fetch(parsedUrl.href, {
      method: req.method,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) BananaOS/1.0 WebBrowser',
        'Accept-Language': 'en-US,en;q=0.9',
      },
      redirect: 'follow'
    });

    const contentType = upstreamResponse.headers.get('content-type') || '';

    // Strip frame and security restrictions
    const headersToIgnore = [
      'x-frame-options',
      'content-security-policy',
      'content-security-policy-report-only',
      'cross-origin-opener-policy',
      'cross-origin-embedder-policy',
      'cross-origin-resource-policy'
    ];

    upstreamResponse.headers.forEach((value, key) => {
      if (!headersToIgnore.includes(key.toLowerCase())) {
        res.setHeader(key, value);
      }
    });

    // Enforce CORS allowance for any embedded AJAX requests
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', '*');

    if (contentType.includes('text/html')) {
      let html = await upstreamResponse.text();
      
      // Inject <base> tag to correctly load relative assets
      const baseTag = `<base href="${parsedUrl.protocol}//${parsedUrl.host}/">`;
      if (html.includes('<head>')) {
        html = html.replace('<head>', `<head>${baseTag}`);
      } else {
        html = `${baseTag}${html}`;
      }

      res.removeHeader('content-length');
      res.removeHeader('content-encoding');
      return res.send(html);
    }

    // Direct binary/asset streaming
    const buffer = await upstreamResponse.arrayBuffer();
    return res.send(Buffer.from(buffer));
  } catch (error) {
    console.error('Proxy Error:', error.message);
    res.status(502).send(`Banana OS Proxy Error: ${error.message}`);
  }
}