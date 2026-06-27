import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { MapContainer, TileLayer } from 'react-leaflet';

function Register() {
    const [formData, setFormData] = useState({
        username: '',
        email: '',
        password: '',
        first_name: '',
        last_name: '',
        vessel_mmsi: ''
    });
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const navigate = useNavigate();

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');
        
        try {
            const data = {
                username: formData.username,
                email: formData.email,
                password: formData.password,
                first_name: formData.first_name || null,
                last_name: formData.last_name || null,
                vessel_mmsi: formData.vessel_mmsi ? parseInt(formData.vessel_mmsi) : null
            };
            
            await axios.post('http://127.0.0.1:8000/api/v1/auth/register', data);
            setSuccess('Регистрация успешна! Перенаправление на вход...');
            setTimeout(() => navigate('/login'), 2000);
        } catch (err) {
            setError(err.response?.data?.detail || 'Ошибка регистрации');
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
                <h2 style={{ textAlign: 'center', marginBottom: '30px' }}>Регистрация</h2>
                
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
                
                {success && (
                    <div style={{
                        backgroundColor: '#efe',
                        color: '#3c3',
                        padding: '10px',
                        borderRadius: '4px',
                        marginBottom: '20px'
                    }}>
                        {success}
                    </div>
                )}
                
                <form onSubmit={handleSubmit}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                        <div>
                            <label>Имя</label>
                            <input
                                type="text"
                                name="first_name"
                                value={formData.first_name}
                                onChange={handleChange}
                                style={inputStyle}
                            />
                        </div>
                        <div>
                            <label>Фамилия</label>
                            <input
                                type="text"
                                name="last_name"
                                value={formData.last_name}
                                onChange={handleChange}
                                style={inputStyle}
                            />
                        </div>
                    </div>
                    
                    <div style={{ marginBottom: '15px' }}>
                        <label>Логин *</label>
                        <input
                            type="text"
                            name="username"
                            value={formData.username}
                            onChange={handleChange}
                            style={inputStyle}
                            required
                        />
                    </div>
                    
                    <div style={{ marginBottom: '15px' }}>
                        <label>Email *</label>
                        <input
                            type="email"
                            name="email"
                            value={formData.email}
                            onChange={handleChange}
                            style={inputStyle}
                            required
                        />
                    </div>
                    
                    <div style={{ marginBottom: '15px' }}>
                        <label>Пароль *</label>
                        <input
                            type="password"
                            name="password"
                            value={formData.password}
                            onChange={handleChange}
                            style={inputStyle}
                            required
                        />
                    </div>
                    
                    <div style={{ marginBottom: '20px' }}>
                        <label>MMSI судна</label>
                        <input
                            type="number"
                            name="vessel_mmsi"
                            value={formData.vessel_mmsi}
                            onChange={handleChange}
                            style={inputStyle}
                            placeholder="Опционально"
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
                            fontSize: '16px'
                        }}
                    >
                        Зарегистрироваться
                    </button>
                </form>
                
                <div style={{ textAlign: 'center', marginTop: '20px' }}>
                    <a href="/login" style={{ color: '#1a1a2e' }}>Войти</a>
                </div>
            </div>
        </div>
    );
}

const inputStyle = {
    width: '100%',
    padding: '8px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    marginTop: '5px'
};

export default Register;