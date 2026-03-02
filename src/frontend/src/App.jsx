import './App.css'

function App() {
  
  const handleUpload = async (e) => {
    e.preventDefault();

    const formData = new FormData(e.target);

    try {
      console.log("Wait...");
      
      const response = await fetch("http://localhost:8000/upload/", {
        method: "POST",
        body: formData,
      });
      
      const data = await response.json();
      console.log("Your data:", data);
      
    } catch (error) {
      console.error("Something went wrong:", error);
    }
  };

  return (
    <main>
      <h1>BoxdMetrics API Tester</h1>
      <p>Watch the console to see the data flow.</p>
      
      {}
      <form onSubmit={handleUpload}>
        <input type="file" name="files" multiple accept=".csv" required />
        <button type="submit">Upload to FastAPI</button>
      </form>
    </main>
  )
}

export default App