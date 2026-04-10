import './App.css'
import { useState } from 'react';

function App() {
  const [displayStats, setDisplayStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const validateFiles = (fileList) => {
    const files = Array.from(fileList);
    const fileNames = files.map(f => f.name.toLowerCase());
    const requiredFiles = ['watched.csv', 'ratings.csv', 'diary.csv'];
    const maxSize = 2 * 1024 * 1024;

    if (files.length === 0) return "Select at least one file.";
    if (files.length !== 3) return `Upload exactly 3 files: watched.csv, ratings.csv, diary.csv.`;

    for (const file of files) {
      if (!file.name.endsWith('.csv')) return `"${file.name}" must be a CSV file.`;
      if (file.size > maxSize) return `"${file.name}" is too large. Max: 2MB.`;
    }

    const missingFiles = requiredFiles.filter(name => !fileNames.includes(name));
    if (missingFiles.length > 0) return `Missing: ${missingFiles.join(', ')}.`;

    return null;
  };

  const getErrorMessage = (status) => {
    const messages = {
      400: "Invalid file format.",
      401: "Session expired. Refresh the page.",
      403: "Access denied.",
      404: "Service unavailable. Try again later.",
      413: "File too large. Max: 2MB.",
      429: "Too many uploads. Wait 60 seconds.",
      500: "Server error. Try again later.",
      502: "Service down. Try again later.",
      503: "Server overloaded. Try again.",
      504: "Request timed out. Check connection."
    };
    return messages[status] || `Error ${status}. Try again.`;
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    const fileInput = e.target.elements.files;
    const validationError = validateFiles(fileInput.files);
    if (validationError) {
      setError(validationError);
      setLoading(false);
      return;
    }

    const formData = new FormData();
    for (let i = 0; i < fileInput.files.length; i++) {
      formData.append("files", fileInput.files[i]);
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);

    try {
      const response = await fetch(import.meta.env.VITE_API_URL, {
        method: "POST",
        headers: { 'X-API-Key': import.meta.env.VITE_API_KEY },
        body: formData,
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const message = getErrorMessage(response.status);
        setError(message);
        return;
      }

      const data = await response.json();
      setDisplayStats(data);
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') {
        setError("Upload timed out.");
      } else {
        setError("Failed to connect. Check internet.");
      }
    } finally {
      setLoading(false);
      e.target.reset();
    }
  };

  return (
    <main className="container">
      <header>
        <h1>BoxdMetrics</h1>
        <p>Upload your watched, ratings, and diary CSVs to see your stats.</p>
      </header>

      <form onSubmit={handleUpload} className="upload-form">
        <div className="file-input-wrapper">
          <input
            type="file"
            name="files"
            multiple
            accept=".csv"
            required
            id="file-upload"
          />
        </div>
        <button type="submit" disabled={loading} className="submit-btn">
          {loading ? "Processing..." : "Generate Dashboard"}
        </button>
      </form>

      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}

      {displayStats && !error && (
        <div className="dashboard">
          <h2>Your Cinematic Profile</h2>

          <div className="bento-grid">
            <div className="bento-card highlight">
              <span className="icon">🎬</span>
              <h3>{displayStats.totalMovies}</h3>
              <p>Total Movies</p>
            </div>

            <div className="bento-card">
              <span className="icon">⭐</span>
              <h3>{displayStats.avgRating}</h3>
              <p>Average Rating</p>
            </div>

            <div className="bento-card">
              <span className="icon">🕰️</span>
              <h3>{displayStats.topDecade}s</h3>
              <p>Favorite Decade</p>
              <small>{displayStats.topCount} films</small>
            </div>

            <div className="bento-card">
              <span className="icon">🍿</span>
              <h3>{displayStats.topDay}</h3>
              <p>Top Watch Day</p>
            </div>

            <div className="bento-card wide">
              <span className="icon">🎞️</span>
              <h3>{displayStats.oldestYear} - {displayStats.newestYear}</h3>
              <p>Era Spanned</p>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}

export default App
