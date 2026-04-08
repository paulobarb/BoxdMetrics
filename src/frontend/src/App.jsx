import './App.css'
import { useState } from 'react';

function App() {

  const [displayStats, setDisplayStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  const handleUpload = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    const formData = new FormData();

    const fileInput = e.target.elements.files; 
    
    for (let i = 0; i < fileInput.files.length; i++) {
      formData.append("files", fileInput.files[i]);
    }

    try {      


      const response = await fetch("/api/upload/", {
        method: "POST",
        body: formData,
      });
      
      const data = await response.json();

      if (!response.ok) {

        const errorMessages = {
          400: "Invalid file format. Please check your CSV files."
          401: "Authentication failed. Please check your credentials."
          413: "File size too large. Maximum allowed is 2MB per file."
          429: "Too many requests. Please wait 60 seconds before trying again."
          500: "Server error processing your files. Please try again later."
        };

        const defaultMsg = `Upload failed (${response.status}). Please check your connection.`;
        const errorMsg = errorMessages[response.status] || defaultMsg;

        if (data.detail) {
          const detailMsg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
          setError(`Error: ${detailMsg}`);
        } else {
          setError(errorMsg);
        }
      }

      console.log("Your data:", data);
      setDisplayStats(data);
    } catch (error) {
      console.error("Network/connection error:", error);
      setError("Unable to connect to the server. Please check your internet connection and try again.");
    } finally{
      setLoading(false);
      e.target.reset(); // Clear the file input
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

      { !loading && error && (
         <div className="error-banner">
              {error}
         </div>
      )}

      { !loading && !error && displayStats && !displayStats.detail && (
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