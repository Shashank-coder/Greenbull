import React, { useState } from 'react';
import axios from 'axios';

function App() {
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);

  const handleQuery = async () => {
    setLoading(true);
    try {
      const token = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImM3ZTA0NDY1NjQ5ZmZhNjA2NTU3NjUwYzdlNjVmMGE4N2FlMDBmZTgiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20iLCJhenAiOiIzMjU1NTk0MDU1OS5hcHBzLmdvb2dsZXVzZXJjb250ZW50LmNvbSIsImF1ZCI6IjMyNTU1OTQwNTU5LmFwcHMuZ29vZ2xldXNlcmNvbnRlbnQuY29tIiwic3ViIjoiMTE0MjkyNjE2MjEwNjg4ODQ2NTc0IiwiZW1haWwiOiJzaGl2YW0uc2hhc2hhbmsxQGdtYWlsLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJhdF9oYXNoIjoiSWRrUzVvcmthU3c3U1d0NzRGTzd4ZyIsImlhdCI6MTc0NDU3NjE5MiwiZXhwIjoxNzQ0NTc5NzkyfQ.0pMb9tF5RZ3qW0XiTaD2NM5F85yn4MMCi6sc8DNkiDyi6yXYkwX-r2zxTiRqpP3TQuATutIIqRz_PyUhbO_dzLAzOzRDv2uVha81af81QSd9M2NjBnVRRZ7maX43sb1etXg5aG_XUYGXgCMPdl1OJ3ITtebXjns8wQi5Bg9QEHxOrrMzkLNpSf8WviYUuB9pM5GB6zs5XCP4ocsy7fgRTVV2R9H93wZ7PmsYSuaIsleK5y7m48SrAJCcRFm78R4qiNkVSPiFboLsvrqDnIacbKNQIXrfZWTYSdIpgEIf0qDQ9s5divkwjhSxwJ_Rk6rgmBDwaqzSGDEy_IFvKobQgw";
      const response = await axios.post('https://semantic-rag-answer-196922301940.us-central1.run.app',
        { query },
        {
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `bearer ${token}`
          }
        }
      );
      setAnswer(response.data.response);
    } catch (error) {
      setAnswer(`Error: ${error.message}`);
    }
    setLoading(false);
  };

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">Stock Expert AI Assistant</h1>
      <input
        className="border p-2 w-full mb-4"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Ask a financial question..."
      />
      <button
        className="bg-blue-500 text-white px-4 py-2 rounded"
        onClick={handleQuery}
        disabled={loading}
      >
        {loading ? 'Loading...' : 'Get Answer'}
      </button>
      {answer && (
        <div className="mt-4 p-4 bg-gray-100 rounded">
          <p>{answer}</p>
        </div>
      )}
    </div>
  );
}

export default App;
