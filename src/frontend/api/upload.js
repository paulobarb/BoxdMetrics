export default async function handler(req, res) {
  const backendIp = process.env.AWS_BACKEND_IP;

  if (!backendIp) {
    return res.status(500).json({ error: 'Backend IP not configured' });
  }

  // Vercel gives us the catch-all path in the query object
  const { path } = req.query;
  const actualPath = Array.isArray(path) ? path.join('/') : path || '';
  const destinationUrl = `http://${backendIp}:8000/${actualPath}`;

  try {
    const fetchOptions = {
      method: req.method,
      headers: {
        ...req.headers,
        'host': `${backendIp}:8000`,
      },
      // Pass the raw, unparsed stream directly to AWS
      body: req.method !== 'GET' && req.method !== 'HEAD' ? req : undefined,
      // Required to use the raw request stream in Node 18+ fetch
      duplex: 'half' 
    };

    const response = await fetch(destinationUrl, fetchOptions);

    // Forward the status code
    res.status(response.status);

    // Copy headers from backend response
    response.headers.forEach((value, key) => {
      if (key.toLowerCase() !== 'content-encoding') {
        res.setHeader(key, value);
      }
    });

    // Send the final data back to the frontend
    const responseData = await response.text();
    res.send(responseData);

  } catch (error) {
    console.error('Proxy error:', error);
    res.status(502).json({ error: 'Bad Gateway', message: error.message });
  }
}

// 🚨 THE CRITICAL FIX FOR CSV UPLOADS 🚨
// This tells Vercel: "Do not parse the body. Leave my files alone!"
export const config = {
  api: {
    bodyParser: false,
  },
};