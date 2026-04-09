/*
export default async function handler(req, res) {
  const backendIp = process.env.AWS_BACKEND_IP;

  // Check if IP exists
  if (!backendIp) {
    return res.status(500).json({ error: 'Backend IP not configured' });
  }

  // Path
  const targetPath = req.url.replace(/^\/api/, '');
  const destinationUrl = `http://${backendIp}:8000${targetPath}`;

  try {
    const chunks = [];
    for await (const chunk of req) {
      chunks.push(chunk);
    }
    const bodyBuffer = chunks.length > 0 ? Buffer.concat(chunks) : undefined;

    const headers = { ...req.headers };
    headers['x-forwarded-for'] = req.headers['x-forwarded-for'] || req.socket.remoteAddress;
    headers['host'] = `${backendIp}:8000`;
    headers['Authorization'] = `Bearer ${process.env.API_SECRET_KEY}`;
    
    if (bodyBuffer) {
      headers['content-length'] = bodyBuffer.length.toString();
    }

    const fetchOptions = {
      method: req.method,
      headers: headers,
      body: bodyBuffer,
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

// CSV file stays untouched by vercel parser
export const config = {
  api: {
    bodyParser: false,
  },
};
*/