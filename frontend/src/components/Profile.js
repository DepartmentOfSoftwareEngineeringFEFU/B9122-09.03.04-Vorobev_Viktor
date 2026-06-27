// frontend/src/components/Profile.js
import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { MapContainer, TileLayer } from 'react-leaflet';

function Profile({ token, setToken }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [editMode, setEditMode] = useState(false);
    const [formData, setFormData] = useState({});
    const navigate = useNavigate();

    useEffect(() => {
        if (!token) {
            navigate('/login');
            return;
        }
        
        fetchUser();
    }, [token]);

    useEffect(() => {
        const isGuest = localStorage.getItem('isGuest') === 'true';
        if (isGuest) {
            navigate('/map');
            return;
        }
        
        if (!token) {
            navigate('/login');
            return;
        }
        
        fetchUser();
    }, [token]);

    const fetchUser = async () => {
        try {
            const response = await axios.get('http://127.0.0.1:8000/api/v1/auth/me', {
                headers: { Authorization: `Bearer ${token}` }
            });
            setUser(response.data);
            setFormData(response.data);
            setLoading(false);
        } catch (err) {
            setError('Ошибка загрузки профиля');
            setLoading(false);
            if (err.response?.status === 401) {
                localStorage.removeItem('token');
                setToken(null);
                navigate('/login');
            }
        }
    };

    const handleUpdate = async () => {
        try {
            const response = await axios.put('http://127.0.0.1:8000/api/v1/auth/me', formData, {
                headers: { Authorization: `Bearer ${token}` }
            });
            setUser(response.data);
            setEditMode(false);
        } catch (err) {
            setError('Ошибка обновления');
        }
    };

    const handleLogout = () => {
        localStorage.removeItem('token');
        setToken(null);
        navigate('/login');
    };

    if (loading) return <div>Загрузка...</div>;

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
                <h2 style={{ textAlign: 'center', marginBottom: '30px' }}>Профиль пользователя</h2>
                
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
                
                {!editMode ? (
                    <>
                        <div style={{ marginBottom: '15px' }}>
                            <strong>Логин:</strong> {user.username}
                        </div>
                        <div style={{ marginBottom: '15px' }}>
                            <strong>Email:</strong> {user.email}
                        </div>
                        <div style={{ marginBottom: '15px' }}>
                            <strong>Имя:</strong> {user.first_name || '-'}
                        </div>
                        <div style={{ marginBottom: '15px' }}>
                            <strong>Фамилия:</strong> {user.last_name || '-'}
                        </div>
                        <div style={{ marginBottom: '15px' }}>
                            <strong>MMSI судна:</strong> {user.vessel_mmsi || '-'}
                        </div>
                        
                        <div style={{ display: 'flex', gap: '10px', marginTop: '20px', flexWrap: 'wrap' }}>
                            <button
                                onClick={() => navigate('/map')}
                                style={{
                                    flex: 1,
                                    padding: '10px',
                                    backgroundColor: '#3b82f6',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer'
                                }}
                            >
                                ← Вернуться к карте
                            </button>
                            <button
                                onClick={() => setEditMode(true)}
                                style={{
                                    flex: 1,
                                    padding: '10px',
                                    backgroundColor: '#10b981',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer'
                                }}
                            >
                                Редактировать
                            </button>
                            <button
                                onClick={handleLogout}
                                style={{
                                    flex: 1,
                                    padding: '10px',
                                    backgroundColor: '#dc2626',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer'
                                }}
                            >
                                Выйти
                            </button>
                        </div>
                    </>
                ) : (
                    <>
                        <div style={{ marginBottom: '15px' }}>
                            <label>Email</label>
                            <input
                                type="email"
                                value={formData.email}
                                onChange={(e) => setFormData({...formData, email: e.target.value})}
                                style={inputStyle}
                            />
                        </div>
                        <div style={{ marginBottom: '15px' }}>
                            <label>Имя</label>
                            <input
                                type="text"
                                value={formData.first_name || ''}
                                onChange={(e) => setFormData({...formData, first_name: e.target.value})}
                                style={inputStyle}
                            />
                        </div>
                        <div style={{ marginBottom: '15px' }}>
                            <label>Фамилия</label>
                            <input
                                type="text"
                                value={formData.last_name || ''}
                                onChange={(e) => setFormData({...formData, last_name: e.target.value})}
                                style={inputStyle}
                            />
                        </div>
                        <div style={{ marginBottom: '20px' }}>
                            <label>MMSI судна</label>
                            <input
                                type="number"
                                value={formData.vessel_mmsi || ''}
                                onChange={(e) => setFormData({...formData, vessel_mmsi: e.target.value})}
                                style={inputStyle}
                            />
                        </div>
                        
                        <div style={{ display: 'flex', gap: '10px' }}>
                            <button
                                onClick={handleUpdate}
                                style={{
                                    flex: 1,
                                    padding: '10px',
                                    backgroundColor: '#10b981',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer'
                                }}
                            >
                                Сохранить
                            </button>
                            <button
                                onClick={() => setEditMode(false)}
                                style={{
                                    flex: 1,
                                    padding: '10px',
                                    backgroundColor: '#6b7280',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer'
                                }}
                            >
                                Отмена
                            </button>
                        </div>
                    </>
                )}
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

export default Profile;