import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

function App() {
  const [data, setData] = useState([]);

  useEffect(() => {
    // 1. Ανοίγουμε τη γραμμή επικοινωνίας (WebSocket) με το Backend μας
    const ws = new WebSocket("ws://127.0.0.1:8000/ws/metrics");

    // 2. Τι κάνουμε όταν έρχεται ένα νέο μήνυμα
    ws.onmessage = (event) => {
      const newData = JSON.parse(event.data);
      
      setData((prevData) => {
        // Κρατάμε μόνο τα τελευταία 50 σημεία για να μην "γονατίσει" η μνήμη του browser
        const updatedData = [...prevData, newData];
        if (updatedData.length > 50) {
          updatedData.shift(); // Πετάμε το παλαιότερο δεδομένο
        }
        return updatedData;
      });
    };

    // 3. Όταν κλείσει η σελίδα, κλείνουμε και τη σύνδεση για να μην έχουμε memory leaks
    return () => ws.close(); 
  }, []);

  return (
    <div style={{ backgroundColor: '#1e1e2f', color: 'white', padding: '40px', minHeight: '100vh', fontFamily: 'sans-serif' }}>
      <h2>🚀 Real-Time Engine Analytics</h2>
      <p style={{ color: '#aaa', marginBottom: '30px' }}>
        Live streaming {data.length > 0 ? "10 updates/sec" : "Connecting..."}
      </p>
      
      <div style={{ width: '100%', height: 450, backgroundColor: '#2a2a3f', padding: '20px', borderRadius: '10px', boxShadow: '0 4px 15px rgba(0,0,0,0.3)' }}>
        <ResponsiveContainer>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#444" />
            {/* Κρύβουμε τον άξονα Χ γιατί ανανεώνεται πολύ γρήγορα */}
            <XAxis dataKey="timestamp" hide /> 
            {/* Ο άξονας Y προσαρμόζεται αυτόματα στις τιμές */}
            <YAxis domain={['dataMin - 10', 'dataMax + 10']} stroke="#aaa" />
            <Tooltip contentStyle={{ backgroundColor: '#333', border: 'none', borderRadius: '5px' }} />
            
            {/* Γραμμή CPU (Γαλάζια) - Κλείνουμε το animation για μέγιστο performance */}
            <Line type="monotone" dataKey="cpu_usage" stroke="#00d8ff" strokeWidth={2} dot={false} isAnimationActive={false} />
            
            {/* Γραμμή Μνήμης (Ροζ) */}
            <Line type="monotone" dataKey="memory_usage" stroke="#ff007a" strokeWidth={2} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default App;
