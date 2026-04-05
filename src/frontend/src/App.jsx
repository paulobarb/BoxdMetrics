import './App.css'
import { useState } from 'react';

function App() {

  const [displayStats, setDisplayData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  const handleUpload = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    const formData = new FormData(e.target);

    try {      

      // await new Promise(resolve => setTimeout(resolve, 2000));

      const response = await fetch("http://localhost:8000/upload/", {
        method: "POST",
        body: formData,
      });
      
      const data = await response.json();

      if(!response.ok) {
        setError(data.detail);
        return;
      };

      console.log("Your data:", data);
      setDisplayData(data);
    } catch (error) {
      console.error("Something went wrong:", error);
      setError("Unable to connect to the server. Please try again.");
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