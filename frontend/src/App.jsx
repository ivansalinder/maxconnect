import { useState, useEffect } from 'react'

function App() {
  const [lobbies, setLobbies] = useState([])

  useEffect(() => {
    // В продакшене (после деплоя) localhost нужно будет заменить на реальный домен сервера
    fetch('http://127.0.0.1:8000/api/lobbies')
      .then(res => res.json())
      .then(data => setLobbies(data))
      .catch(err => console.error("Ошибка загрузки данных:", err))
  }, [])

  const handleJoin = async (lobbyId) => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/join', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          lobby_id: lobbyId,
          user_id: "test_user_id", // В финальной версии берется из МАХ Bridge
          organizer_chat_id: "test_org_id" // Берется из данных лобби
        }),
      });

      if (response.ok) {
        alert('Заявка отправлена! Проверьте чат-бот.');
      } else {
        alert('Ошибка при отправке заявки.');
      }
    } catch (error) {
      console.error('Ошибка сети:', error);
      alert('Ошибка соединения с сервером.');
    }
  };

  return (
    <div style={{ 
      padding: '20px', 
      fontFamily: 'sans-serif', 
      maxWidth: '600px', 
      margin: '0 auto',
      backgroundColor: '#f8f9fa',
      minHeight: '100vh',
      color: '#333'
    }}>
      <h2 style={{ textAlign: 'center', color: '#333' }}>Радар досуга: Уфа</h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
        {lobbies.map(lobby => (
          <div key={lobby.id} style={{ 
            border: '1px solid #ddd', 
            padding: '15px', 
            borderRadius: '12px', 
            boxShadow: '0 4px 6px rgba(0,0,0,0.05)',
            backgroundColor: '#ffffff'
          }}>
            <h3 style={{ margin: '0 0 10px 0', color: '#6200ee' }}>{lobby.title}</h3>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '14px', color: '#555', marginBottom: '5px' }}>
              <span>📍 {lobby.location}</span>
              <span>🕒 {lobby.time}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '14px', color: '#555', marginBottom: '15px' }}>
              <span>📂 {lobby.category}</span>
              <span>👥 {lobby.participants} / {lobby.max_participants} чел.</span>
            </div>
            <button 
              onClick={() => handleJoin(lobby.id)}
              style={{ 
                background: '#6200ee', 
                color: 'white', 
                padding: '10px', 
                border: 'none', 
                borderRadius: '8px', 
                width: '100%', 
                cursor: 'pointer', 
                fontWeight: 'bold' 
            }}>
              Присоединиться
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

export default App