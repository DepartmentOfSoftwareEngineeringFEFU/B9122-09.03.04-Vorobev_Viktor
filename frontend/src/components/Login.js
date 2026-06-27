// frontend/src/components/Login.js
import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { MapContainer, TileLayer } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

function Login({ setToken }) {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const navigate = useNavigate();

    const clearGuestData = async () => {
        try {
            await axios.post('http://127.0.0.1:8000/api/v1/auth/clear-guest-data');
            console.log('Гостевые данные очищены');
        } catch (err) {
            console.error('Ошибка очистки гостевых данных:', err);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        
        try {
            await clearGuestData();
            
            const formData = new FormData();
            formData.append('username', username);
            formData.append('password', password);
            
            const response = await axios.post('http://127.0.0.1:8000/api/v1/auth/login', formData);
            const { access_token } = response.data;
            
            localStorage.setItem('token', access_token);
            localStorage.removeItem('isGuest');
            setToken(access_token);
            navigate('/map');
        } catch (err) {
            setError(err.response?.data?.detail || 'Ошибка входа');
        }
    };

    const handleGuestLogin = async () => {
        try {
            await clearGuestData();
            
            const guestToken = 'guest_token_' + Date.now();
            localStorage.setItem('token', guestToken);
            localStorage.setItem('isGuest', 'true');
            setToken(guestToken);
            navigate('/map');
        } catch (err) {
            console.error('Ошибка гостевого входа:', err);
            setError('Ошибка при входе как гость');
        }
    };

    return (
        <div style={{ position: 'relative', height: '100vh', width: '100%' }}>
            <MapContainer
                center={[43.115, 131.885]}
                zoom={13}
                style={{ height: '100%', width: '100%', position: 'absolute', top: 0, left: 0 }}
                zoomControl={false}
                attributionControl={false}
            >
                <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            </MapContainer>
            
            <div style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                zIndex: 1000,
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                padding: '40px',
                borderRadius: '12px',
                boxShadow: '0 4px 20px rgba(0,0,0,0.2)',
                width: '400px',
                backdropFilter: 'blur(10px)'
            }}>
                <h2 style={{ textAlign: 'center', marginBottom: '30px', color: '#1a1a2e' }}>Вход в систему</h2>
                
                {error && (
                    <div style={{
                        backgroundColor: '#fee',
                        color: '#c33',
                        padding: '10px',
                        borderRadius: '4px',
                        marginBottom: '20px'
                    }}>
                        {error}
                    </div>
                )}
                
                <form onSubmit={handleSubmit}>
                    <div style={{ marginBottom: '15px' }}>
                        <label style={{ display: 'block', marginBottom: '5px' }}>Логин</label>
                        <input
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            style={{
                                width: '100%',
                                padding: '8px',
                                border: '1px solid #ddd',
                                borderRadius: '4px'
                            }}
                            required
                        />
                    </div>
                    
                    <div style={{ marginBottom: '20px' }}>
                        <label style={{ display: 'block', marginBottom: '5px' }}>Пароль</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            style={{
                                width: '100%',
                                padding: '8px',
                                border: '1px solid #ddd',
                                borderRadius: '4px'
                            }}
                            required
                        />
                    </div>
                    
                    <button
                        type="submit"
                        style={{
                            width: '100%',
                            padding: '10px',
                            backgroundColor: '#1a1a2e',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '16px',
                            marginBottom: '10px'
                        }}
                    >
                        Войти
                    </button>
                    
                    <button
                        type="button"
                        onClick={handleGuestLogin}
                        style={{
                            width: '100%',
                            padding: '10px',
                            backgroundColor: '#6b7280',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '16px'
                        }}
                    >
                        Войти как гость
                    </button>
                </form>
                
                <div style={{ textAlign: 'center', marginTop: '20px' }}>
                    <a href="/register" style={{ color: '#1a1a2e' }}>Нет аккаунта? Зарегистрироваться</a>
                </div>
            </div>
        </div>
    );
}

export default Login;