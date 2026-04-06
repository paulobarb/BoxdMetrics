export default async function handler(req, res) {
  const backendIp = process.env.AWS_BACKEND_IP;

  // Check if IP exists
  if (!backendIp) {
    return res.status(500).json({ error: 'Backend IP not configured' });
  }

  // Path
  const targetPath = req.url.replace(/^\/api/, '');
  const destinationUrl = `http://${backendIp}:8000${targetPath}`

  try {
    const fetchOptions = {
      method: req.method,
      headers: {
        ...req.headers,
        'host': `${backendIp}:8000`,
      },
      // Pass the raw, unparsed stream directly to AWS
      body: req.method !== 'GET' && req.method !== 'HEAD' ? req : undefined,
      duplex: 'half' 
    };

    const response = await fetch(destinationUrl, fetchOptions);

    res.status(response.status);

    response.headers.forEach((value, key) => {
      if (key.toLowerCase() !== 'content-encoding') {
        res.setHeader(key, value);
      }
    });

    const responseData = await response.text();
    res.send(responseData);

  } catch (error) {
    console.error('Proxy error:', error);
    res.status(502).json({ error: 'Bad Gateway', message: error.message });
  }
}

// CSV file stays untouched by vercel
export const config = {
  api: {
    bodyParser: false,
  },
};