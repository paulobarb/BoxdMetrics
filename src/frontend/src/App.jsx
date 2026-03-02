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
      setError(error);
    } finally{
      setLoading(false);
      e.target.reset(); // Clear the file input
    }
  };

  return (
    <main>
      <h1>BoxdMetrics</h1>

      <form onSubmit={handleUpload}>
        <input 
          type="file"
          name="files" 
          multiple accept=".csv"
          required />
        <button type="submit" disabled={loading}>
          {loading ? "Processing..." : "Upload"}
        </button>
      </form>

      { !loading && error && (
         <div style={{ color: '#ff6b6b', padding: '10px', marginTop: '30px', border: '1px solid #ff6b6b', borderRadius: '5px' }}>
              {"Unable to connect to the server. Please try again."}
            </div>
      )}

      { !loading && !error && displayStats && (
      <div style={{ marginTop: '30px' }}>
          <h2>Your Stats</h2>
          
          {displayStats.detail ? (
            <div style={{ color: '#ff6b6b', padding: '10px', border: '1px solid #ff6b6b', borderRadius: '5px' }}>
              {displayStats.detail}
            </div>
          ) : (
            <div className="showStatsInside">
              
              <div>
                <strong>Total Movies:</strong> {displayStats.totalMovies}
              </div>
              
              <div>
                <strong>Average Rating:</strong> {displayStats.avgRating} / 5
              </div>
              
              <div>
                <strong>Favorite Decade:</strong> {displayStats.topDecade}s 
                <span style={{ fontSize: '0.9rem', color: '#aaa', marginLeft: '8px' }}>
                  ({displayStats.topCount} movies)
                </span>
              </div>
              
              <div>
                <strong>Top Watch Day:</strong> {displayStats.topDay}
              </div>
              
              <div>
                <strong>Era Spanned:</strong> {displayStats.oldestYear} to {displayStats.newestYear}
              </div>

            </div>
          )}
        </div>
      )}
    </main>
  )
}

export default App