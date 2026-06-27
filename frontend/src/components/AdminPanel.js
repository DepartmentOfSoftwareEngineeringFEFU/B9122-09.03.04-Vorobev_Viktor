import React, { useState, useEffect } from 'react';
import axios from 'axios';

function AdminPanel({ onClose }) {
    const [adminKey, setAdminKey] = useState('');
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [speedLimits, setSpeedLimits] = useState({});
    const [courseDeviation, setCourseDeviation] = useState({ allowed_degrees: 30.0 });
    const [speedMultiplier, setSpeedMultiplier] = useState(1.5);
    const [alerts, setAlerts] = useState([]);
    const [stats, setStats] = useState({});
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('limits');
    const [message, setMessage] = useState(null);
    
    const [vessels, setVessels] = useState([]);
    const [newAlert, setNewAlert] = useState({
        mmsi: '',
        alert_type: 'manual',
        severity: 'warning',
        title: '',
        description: '',
        latitude: '',
        longitude: ''
    });
    const [creatingAlert, setCreatingAlert] = useState(false);

    const getAuthHeaders = () => {
        return { Authorization: `Bearer ${adminKey}` };
    };

    const fetchData = async () => {
        try {
            const headers = getAuthHeaders();
            const [limitsRes, deviationRes, multiplierRes, alertsRes, statsRes] = await Promise.all([
                axios.get('http://127.0.0.1:8000/api/v1/admin/settings/speed-limits', { headers }),
                axios.get('http://127.0.0.1:8000/api/v1/admin/settings/course-deviation', { headers }),
                axios.get('http://127.0.0.1:8000/api/v1/admin/settings/speed-multiplier', { headers }),
                axios.get('http://127.0.0.1:8000/api/v1/admin/alerts?limit=50', { headers }),
                axios.get('http://127.0.0.1:8000/api/v1/admin/stats', { headers })
            ]);
            
            setSpeedLimits(limitsRes.data);
            setCourseDeviation(deviationRes.data);
            setSpeedMultiplier(multiplierRes.data.multiplier);
            setAlerts(alertsRes.data);
            setStats(statsRes.data);
            setLoading(false);
        } catch (err) {
            console.error('Ошибка загрузки данных:', err);
            if (err.response?.status === 403 || err.response?.status === 401) {
                setMessage({ type: 'error', text: 'Неверный пароль' });
                setIsAuthenticated(false);
            } else {
                setMessage({ type: 'error', text: 'Ошибка загрузки данных' });
            }
            setLoading(false);
        }
    };

    const fetchVessels = async () => {
        try {
            const headers = getAuthHeaders();
            const response = await axios.get('http://127.0.0.1:8000/api/v1/admin/vessels', { headers });
            setVessels(response.data);
        } catch (err) {
            console.error('Ошибка загрузки судов:', err);
        }
    };

    const handleLogin = () => {
        setIsAuthenticated(true);
        setLoading(true);
        fetchData();
    };

    const updateSpeedLimits = async () => {
        try {
            await axios.put('http://127.0.0.1:8000/api/v1/admin/settings/speed-limits', {
                speed_limits: speedLimits
            }, { headers: getAuthHeaders() });
            setMessage({ type: 'success', text: 'Скоростные лимиты обновлены' });
            setTimeout(() => setMessage(null), 3000);
        } catch (err) {
            setMessage({ type: 'error', text: 'Ошибка обновления скоростных лимитов' });
        }
    };

    const updateCourseDeviation = async () => {
        try {
            await axios.put('http://127.0.0.1:8000/api/v1/admin/settings/course-deviation', {
                allowed_degrees: courseDeviation.allowed_degrees
            }, { headers: getAuthHeaders() });
            setMessage({ type: 'success', text: 'Настройки отклонения по курсу обновлены' });
            setTimeout(() => setMessage(null), 3000);
        } catch (err) {
            setMessage({ type: 'error', text: 'Ошибка обновления настроек отклонения' });
        }
    };

    const updateSpeedMultiplier = async () => {
        try {
            await axios.put('http://127.0.0.1:8000/api/v1/admin/settings/speed-multiplier', {
                multiplier: speedMultiplier
            }, { headers: getAuthHeaders() });
            setMessage({ type: 'success', text: 'Множитель критической скорости обновлён' });
            setTimeout(() => setMessage(null), 3000);
        } catch (err) {
            setMessage({ type: 'error', text: 'Ошибка обновления множителя' });
        }
    };

    const clearAlerts = async () => {
        if (window.confirm('Очистить все предупреждения?')) {
            try {
                await axios.delete('http://127.0.0.1:8000/api/v1/admin/alerts', { headers: getAuthHeaders() });
                setMessage({ type: 'success', text: 'Все предупреждения очищены' });
                fetchData();
                setTimeout(() => setMessage(null), 3000);
            } catch (err) {
                setMessage({ type: 'error', text: 'Ошибка очистки предупреждений' });
            }
        }
    };

    const handleCreateAlert = async () => {
        if (!newAlert.mmsi || !newAlert.title || !newAlert.description) {
            setMessage({ type: 'error', text: 'Заполните все обязательные поля' });
            return;
        }
        
        setCreatingAlert(true);
        try {
            const headers = getAuthHeaders();
            await axios.post('http://127.0.0.1:8000/api/v1/admin/alerts', {
                mmsi: parseInt(newAlert.mmsi),
                alert_type: newAlert.alert_type,
                severity: newAlert.severity,
                title: newAlert.title,
                description: newAlert.description,
                latitude: newAlert.latitude ? parseFloat(newAlert.latitude) : null,
                longitude: newAlert.longitude ? parseFloat(newAlert.longitude) : null
            }, { headers });
            
            setMessage({ type: 'success', text: 'Предупреждение успешно создано!' });
            setNewAlert({
                mmsi: '',
                alert_type: 'manual',
                severity: 'warning',
                title: '',
                description: '',
                latitude: '',
                longitude: ''
            });
            fetchData();
            setTimeout(() => setMessage(null), 3000);
        } catch (err) {
            setMessage({ type: 'error', text: 'Ошибка создания предупреждения' });
        } finally {
            setCreatingAlert(false);
        }
    };

    if (!isAuthenticated) {
        return (
            <div style={overlayStyle}>
                <div style={panelStyle}>
                    <div style={headerStyle}>
                        <h2>Панель администратора</h2>
                        <button onClick={onClose} style={closeButtonStyle}>✕</button>
                    </div>
                    <div style={contentStyle}>
                        <h3>Введите ключ доступа</h3>
                        <input
                            type="password"
                            value={adminKey}
                            onChange={(e) => setAdminKey(e.target.value)}
                            placeholder="Ключ доступа"
                            style={{ width: '100%', padding: '10px', marginBottom: '15px', borderRadius: '4px', border: '1px solid #ddd' }}
                        />
                        <button onClick={handleLogin} style={saveButtonStyle}>Войти</button>
                    </div>
                </div>
            </div>
        );
    }

    if (loading) return <div style={overlayStyle}><div style={panelStyle}>Загрузка...</div></div>;

    return (
        <div style={overlayStyle}>
            <div style={panelStyle}>
                <div style={headerStyle}>
                    <h2>Панель администратора</h2>
                    <button onClick={onClose} style={closeButtonStyle}>✕</button>
                </div>
                
                {message && (
                    <div style={{
                        padding: '10px',
                        backgroundColor: message.type === 'success' ? '#d4edda' : '#f8d7da',
                        color: message.type === 'success' ? '#155724' : '#721c24',
                        borderRadius: '4px',
                        marginBottom: '15px'
                    }}>
                        {message.text}
                    </div>
                )}
                
                <div style={tabBarStyle}>
                    <button onClick={() => setActiveTab('limits')} style={{...tabStyle, ...(activeTab === 'limits' ? activeTabStyle : {})}}>Скоростные лимиты</button>
                    <button onClick={() => setActiveTab('deviation')} style={{...tabStyle, ...(activeTab === 'deviation' ? activeTabStyle : {})}}>Отклонение по курсу</button>
                    <button onClick={() => setActiveTab('alerts')} style={{...tabStyle, ...(activeTab === 'alerts' ? activeTabStyle : {})}}>Предупреждения ({stats.total_alerts || 0})</button>
                    <button onClick={() => setActiveTab('stats')} style={{...tabStyle, ...(activeTab === 'stats' ? activeTabStyle : {})}}>Статистика</button>
                    <button onClick={() => {
                        setActiveTab('create');
                        fetchVessels();
                    }} style={{...tabStyle, ...(activeTab === 'create' ? activeTabStyle : {})}}>Создать предупреждение</button>
                </div>
                
                <div style={contentStyle}>
                    {activeTab === 'limits' && (
                        <div>
                            <h3>Скоростные лимиты (узлы)</h3>
                            {Object.entries(speedLimits).map(([type, limit]) => (
                                <div key={type} style={rowStyle}>
                                    <label style={labelStyle}>{getVesselTypeName(type)}:</label>
                                    <input
                                        type="number"
                                        step="0.5"
                                        value={limit}
                                        onChange={(e) => setSpeedLimits({...speedLimits, [type]: parseFloat(e.target.value)})}
                                        style={inputStyle}
                                    />
                                </div>
                            ))}
                            <button onClick={updateSpeedLimits} style={saveButtonStyle}>Сохранить лимиты</button>
                        </div>
                    )}
                    
                    {activeTab === 'deviation' && (
                        <div>
                            <h3>Настройки отклонения по курсу</h3>
                            <div style={rowStyle}>
                                <label style={labelStyle}>Допустимое отклонение (градусы):</label>
                                <input
                                    type="number"
                                    step="5"
                                    min="0"
                                    max="180"
                                    value={courseDeviation.allowed_degrees}
                                    onChange={(e) => setCourseDeviation({ allowed_degrees: parseFloat(e.target.value) })}
                                    style={inputStyle}
                                />
                            </div>
                            <div style={{ fontSize: '12px', color: '#666', marginBottom: '15px' }}>
                                Максимальное отклонение курса судна от направления маршрута, при котором нарушение НЕ фиксируется.
                                Рекомендуемое значение: 30-45 градусов.
                            </div>
                            <div style={rowStyle}>
                                <label style={labelStyle}>Множитель критической скорости:</label>
                                <input
                                    type="number"
                                    step="0.1"
                                    min="1.0"
                                    value={speedMultiplier}
                                    onChange={(e) => setSpeedMultiplier(parseFloat(e.target.value))}
                                    style={inputStyle}
                                />
                            </div>
                            <div style={{ fontSize: '12px', color: '#666', marginBottom: '15px' }}>
                                Превышение скорости в N раз от лимита считается критическим нарушением.
                                Рекомендуемое значение: 1.5 (50% превышения).
                            </div>
                            <button onClick={updateCourseDeviation} style={saveButtonStyle}>Сохранить настройки отклонения</button>
                            <button onClick={updateSpeedMultiplier} style={{...saveButtonStyle, marginLeft: '10px'}}>Сохранить множитель</button>
                        </div>
                    )}
                    
                    {activeTab === 'alerts' && (
                        <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <h3>Последние предупреждения</h3>
                                <button onClick={clearAlerts} style={{...saveButtonStyle, backgroundColor: '#dc2626'}}>Очистить все</button>
                            </div>
                            {alerts.length === 0 ? (
                                <p>Нет предупреждений</p>
                            ) : (
                                <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                                    {alerts.map(alert => (
                                        <div key={alert.id} style={{
                                            padding: '10px',
                                            marginBottom: '10px',
                                            borderLeft: `4px solid ${alert.severity === 'critical' ? '#dc2626' : '#f59e0b'}`,
                                            backgroundColor: '#f9fafb',
                                            borderRadius: '4px'
                                        }}>
                                            <div><strong>{alert.title}</strong> - {alert.severity === 'critical' ? 'Критическое' : 'Предупреждение'}</div>
                                            <div style={{ fontSize: '12px', color: '#666' }}>{alert.description}</div>
                                            <div style={{ fontSize: '11px', color: '#999' }}>MMSI: {alert.mmsi} | {new Date(alert.timestamp).toLocaleString()}</div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                    
                    {activeTab === 'stats' && (
                        <div>
                            <h3>Статистика системы</h3>
                            <div style={rowStyle}><strong>Судов:</strong> {stats.vessels}</div>
                            <div style={rowStyle}><strong>Позиций:</strong> {stats.positions}</div>
                            <div style={rowStyle}><strong>Исторических маршрутов:</strong> {stats.historical_routes}</div>
                            <div style={rowStyle}><strong>Всего предупреждений:</strong> {stats.total_alerts}</div>
                            <div style={rowStyle}><strong>Неподтверждённых предупреждений:</strong> {stats.unacknowledged_alerts}</div>
                        </div>
                    )}
                    
                    {activeTab === 'create' && (
                        <div>
                            <h3>Создать ручное предупреждение</h3>
                            
                            <div style={rowStyle}>
                                <label style={labelStyle}>MMSI судна *:</label>
                                <select
                                    value={newAlert.mmsi}
                                    onChange={(e) => setNewAlert({...newAlert, mmsi: e.target.value})}
                                    style={{...inputStyle, width: '220px'}}
                                >
                                    <option value="">Выберите судно...</option>
                                    {vessels.map(v => (
                                        <option key={v.mmsi} value={v.mmsi}>
                                            {v.mmsi} - {v.name} ({getVesselTypeName(v.vessel_type)})
                                        </option>
                                    ))}
                                </select>
                            </div>
                            
                            <div style={rowStyle}>
                                <label style={labelStyle}>Тип предупреждения *:</label>
                                <select
                                    value={newAlert.alert_type}
                                    onChange={(e) => setNewAlert({...newAlert, alert_type: e.target.value})}
                                    style={{...inputStyle, width: '220px'}}
                                >
                                    <option value="manual">Ручное (Общее)</option>
                                    <option value="speed_violation">Превышение скорости</option>
                                    <option value="route_deviation">Отклонение от маршрута</option>
                                </select>
                            </div>
                            
                            <div style={rowStyle}>
                                <label style={labelStyle}>Серьёзность *:</label>
                                <select
                                    value={newAlert.severity}
                                    onChange={(e) => setNewAlert({...newAlert, severity: e.target.value})}
                                    style={{...inputStyle, width: '220px'}}
                                >
                                    <option value="warning">Предупреждение (Жёлтый)</option>
                                    <option value="critical">Критическое (Красный)</option>
                                </select>
                            </div>
                            
                            <div style={rowStyle}>
                                <label style={labelStyle}>Заголовок *:</label>
                                <input
                                    type="text"
                                    value={newAlert.title}
                                    onChange={(e) => setNewAlert({...newAlert, title: e.target.value})}
                                    style={{...inputStyle, width: '300px'}}
                                    placeholder="Заголовок предупреждения"
                                />
                            </div>
                            
                            <div style={rowStyle}>
                                <label style={labelStyle}>Описание *:</label>
                                <textarea
                                    value={newAlert.description}
                                    onChange={(e) => setNewAlert({...newAlert, description: e.target.value})}
                                    style={{...inputStyle, width: '300px', height: '60px'}}
                                    placeholder="Описание предупреждения"
                                />
                            </div>
                            
                            <div style={rowStyle}>
                                <label style={labelStyle}>Широта (опционально):</label>
                                <input
                                    type="number"
                                    step="0.0001"
                                    value={newAlert.latitude}
                                    onChange={(e) => setNewAlert({...newAlert, latitude: e.target.value})}
                                    style={inputStyle}
                                    placeholder="Широта"
                                />
                            </div>
                            
                            <div style={rowStyle}>
                                <label style={labelStyle}>Долгота (опционально):</label>
                                <input
                                    type="number"
                                    step="0.0001"
                                    value={newAlert.longitude}
                                    onChange={(e) => setNewAlert({...newAlert, longitude: e.target.value})}
                                    style={inputStyle}
                                    placeholder="Долгота"
                                />
                            </div>
                            
                            <button 
                                onClick={handleCreateAlert} 
                                disabled={creatingAlert}
                                style={{...saveButtonStyle, backgroundColor: '#3b82f6'}}
                            >
                                {creatingAlert ? 'Создание...' : 'Создать предупреждение'}
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

const getVesselTypeName = (type) => {
    const types = {
        'tanker': 'Танкер',
        'container': 'Контейнеровоз',
        'passenger': 'Пассажирское',
        'tug': 'Буксир',
        'fishing': 'Рыболовное',
        'cargo': 'Грузовое',
        'wig': 'Экраноплан',
        'hsc': 'Скоростное судно',
        'military': 'Военное',
        'sailing': 'Парусное',
        'pleasure': 'Прогулочное',
        'pilot': 'Лоцманское',
        'sar': 'Спасательное',
        'dredger': 'Земснаряд',
        'diving': 'Водолазное',
        'fire': 'Пожарное',
        'port_tender': 'Портовое',
        'other': 'Другое'
    };
    return types[type] || type || 'Не указан';
};

const overlayStyle = {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.5)',
    zIndex: 2000,
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center'
};

const panelStyle = {
    backgroundColor: 'white',
    borderRadius: '12px',
    width: '680px',
    maxWidth: '90%',
    maxHeight: '80vh',
    overflow: 'auto',
    boxShadow: '0 4px 20px rgba(0,0,0,0.3)'
};

const headerStyle = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '15px 20px',
    borderBottom: '1px solid #eee',
    backgroundColor: '#1a1a2e',
    color: 'white',
    borderRadius: '12px 12px 0 0'
};

const closeButtonStyle = {
    background: 'none',
    border: 'none',
    fontSize: '20px',
    cursor: 'pointer',
    color: 'white'
};

const tabBarStyle = {
    display: 'flex',
    borderBottom: '1px solid #ddd',
    backgroundColor: '#f8f9fa',
    flexWrap: 'wrap'
};

const tabStyle = {
    padding: '10px 20px',
    cursor: 'pointer',
    border: 'none',
    backgroundColor: 'transparent',
    fontSize: '14px'
};

const activeTabStyle = {
    borderBottom: '2px solid #1a1a2e',
    color: '#1a1a2e',
    fontWeight: 'bold'
};

const contentStyle = {
    padding: '20px'
};

const rowStyle = {
    marginBottom: '10px',
    display: 'flex',
    alignItems: 'center',
    flexWrap: 'wrap'
};

const labelStyle = {
    width: '220px',
    fontWeight: 'bold'
};

const inputStyle = {
    padding: '5px 10px',
    borderRadius: '4px',
    border: '1px solid #ddd',
    width: '120px'
};

const saveButtonStyle = {
    padding: '8px 16px',
    backgroundColor: '#10b981',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    marginTop: '15px'
};

export default AdminPanel;