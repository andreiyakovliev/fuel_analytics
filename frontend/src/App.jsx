import { useEffect, useState } from 'react';
import { apiRequest } from './services/api';

function App() {
  const [status, setStatus] = useState('Тестуємо зв’язок з API...');

  useEffect(() => {
    // Робимо тестовий запит до /cities (поверне 401 або список)
    apiRequest('/cities')
      .then((data) => {
        console.log('Відповідь API:', data);
        setStatus('Зв’язок успішний!');
      })
      .catch((err) => {
        console.log('Помилка API:', err.message);
        setStatus(`Запит відпрацював: ${err.message}`);
      });
  }, []);

  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif' }}>
      <h1>Перевірка API</h1>
      <p>{status}</p>
    </div>
  );
}

export default App;