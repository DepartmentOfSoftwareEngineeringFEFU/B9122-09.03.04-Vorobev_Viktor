import React, { useEffect, useState } from 'react';
import axios from 'axios';

function AlertsPanel({ selectedVessel }) {
    const [alerts, setAlerts] = useState([]);
    const [myVesselAlerts, setMyVesselAlerts] = useState([]);
    const [myVesselMmsi, setMyVesselMmsi] = useState(null);
    const [expanded, setExpanded] = useState(true);

    const getAuthHeaders = () => {
        return {};
    };

    const fetchAlerts = async () => {
        try {
            const url = selectedVessel 
                ? `http://127.0.0.1:8000/api/v1/alerts/?mmsi=${selectedVessel.mmsi}`
                : 'http://127.0.0.1:8000/api/v1/alerts/';
            const response = await axios.get(url);
            setAlerts(response.data);
        } catch (error) {
            console.error('Ошибка загрузки предупреждений:', error);
        }
    };

    const fetchMyVesselAlerts = async () => {
        if (!myVesselMmsi) return;
        
        try {
            const headers = getAuthHeaders();
            const response = await axios.get(`http://127.0.0.1:8000/api/v1/alerts/?mmsi=${myVesselMmsi}`, { headers });
            setMyVesselAlerts(response.data);
        } catch (error) {
            console.error('Ошибка загрузки уведомлений для своего судна:', error);
        }
    };

    useEffect(() => {
        if (myVesselMmsi) {
            fetchMyVesselAlerts();
            const interval = setInterval(fetchMyVesselAlerts, 10000);
            return () => clearInterval(interval);
        }
    }, [myVesselMmsi]);

    useEffect(() => {
        fetchAlerts();
        const interval = setInterval(fetchAlerts, 10000);
        return () => clearInterval(interval);
    }, [selectedVessel]);

    const acknowledgeAlert = async (alertId) => {
        try {
            await axios.post(`http://127.0.0.1:8000/api/v1/alerts/${alertId}/acknowledge?user_id=1`);
            setAlerts(alerts.filter(a => a.id !== alertId));
        } catch (error) {
            console.error('Ошибка подтверждения:', error);
        }
    };

    const getSeverityColor = (severity) => {
        switch (severity) {
            case 'critical': return '#dc2626';
            case 'warning': return '#f59e0b';
            default: return '#3b82f6';
        }
    };

    const getAlertTypeText = (type) => {
        switch (type) {
            case 'speed_violation': return 'Превышение скорости';
            case 'route_deviation': return 'Отклонение от маршрута';
            default: return 'Предупреждение';
        }
    };

    const hasMyVesselAlerts = myVesselAlerts.length > 0;

    return (
        <div style={{
            position: 'absolute',
            top: 80,
            right: 20,
            zIndex: 1000,
            backgroundColor: 'white',
            borderRadius: '12px',
            boxShadow: '0 4px 20px rgba(0,0,0,0.2)',
            width: '320px',
            maxWidth: '90%',
            transition: 'all 0.3s'
        }}>
            <div style={{
                padding: '12px 16px',
                backgroundColor: '#1a1a2e',
                color: 'white',
                borderRadius: '12px 12px 0 0',
                cursor: 'pointer',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
            }} onClick={() => setExpanded(!expanded)}>
                <span>
                    Предупреждения
                    {hasMyVesselAlerts && ` (⭐ ${myVesselAlerts.length})`}
                    {selectedVessel && !hasMyVesselAlerts && ` - ${selectedVessel.name}`}
                </span>
                <span>{expanded ? '▲' : '▼'}</span>
            </div>
            
            {expanded && (
                <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                    {hasMyVesselAlerts && (
                        <div style={{ backgroundColor: '#f0fdf4', borderBottom: '1px solid #dcfce7' }}>
                            <div style={{
                                padding: '8px 12px',
                                backgroundColor: '#dcfce7',
                                fontSize: '12px',
                                fontWeight: 'bold',
                                color: '#166534'
                            }}>
                                ⭐ Ваше судно (MMSI: {myVesselMmsi})
                            </div>
                            {myVesselAlerts.map(alert => (
                                <div key={alert.id} style={{
                                    padding: '12px 16px',
                                    borderBottom: '1px solid #eee',
                                    borderLeft: `4px solid ${getSeverityColor(alert.severity)}`,
                                    margin: '4px 8px',
                                    borderRadius: '4px',
                                    backgroundColor: 'white'
                                }}>
                                    <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                                        {getAlertTypeText(alert.type)} - {alert.severity === 'critical' ? 'Критическое' : 'Предупреждение'}
                                    </div>
                                    <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px' }}>
                                        {alert.description}
                                    </div>
                                    {alert.parameters && alert.parameters.excess_percent && (
                                        <div style={{ fontSize: '11px', color: '#999', marginBottom: '8px' }}>
                                            Превышение: {alert.parameters.excess_percent}%
                                        </div>
                                    )}
                                    {alert.parameters && alert.parameters.deviation_km && (
                                        <div style={{ fontSize: '11px', color: '#999', marginBottom: '8px' }}>
                                            Отклонение: {alert.parameters.deviation_km} км
                                        </div>
                                    )}
                                    <div style={{ fontSize: '11px', color: '#999', marginBottom: '8px' }}>
                                        {new Date(alert.timestamp).toLocaleString()}
                                    </div>
                                    <button
                                        onClick={() => acknowledgeAlert(alert.id)}
                                        style={{
                                            padding: '4px 12px',
                                            fontSize: '11px',
                                            backgroundColor: '#3b82f6',
                                            color: 'white',
                                            border: 'none',
                                            borderRadius: '4px',
                                            cursor: 'pointer'
                                        }}
                                    >
                                        Подтвердить
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                    
                    {selectedVessel && selectedVessel.mmsi !== myVesselMmsi && (
                        <>
                            <div style={{
                                padding: '8px 12px',
                                backgroundColor: '#f1f5f9',
                                fontSize: '12px',
                                fontWeight: 'bold',
                                color: '#334155',
                                borderBottom: '1px solid #e2e8f0'
                            }}>
                                Выбранное судно: {selectedVessel.name}
                            </div>
                            {alerts.length === 0 ? (
                                <div style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
                                    Нет предупреждений
                                </div>
                            ) : (
                                alerts.map(alert => (
                                    <div key={alert.id} style={{
                                        padding: '12px 16px',
                                        borderBottom: '1px solid #eee',
                                        borderLeft: `4px solid ${getSeverityColor(alert.severity)}`
                                    }}>
                                        <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                                            {getAlertTypeText(alert.type)} - {alert.severity === 'critical' ? 'Критическое' : 'Предупреждение'}
                                        </div>
                                        <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px' }}>
                                            {alert.description}
                                        </div>
                                        <div style={{ fontSize: '11px', color: '#999', marginBottom: '8px' }}>
                                            {new Date(alert.timestamp).toLocaleString()}
                                        </div>
                                        <button
                                            onClick={() => acknowledgeAlert(alert.id)}
                                            style={{
                                                padding: '4px 12px',
                                                fontSize: '11px',
                                                backgroundColor: '#3b82f6',
                                                color: 'white',
                                                border: 'none',
                                                borderRadius: '4px',
                                                cursor: 'pointer'
                                            }}
                                        >
                                            Подтвердить
                                        </button>
                                    </div>
                                ))
                            )}
                        </>
                    )}
                    
                    {!hasMyVesselAlerts && !selectedVessel && (
                        <div style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
                            Нет активных предупреждений
                        </div>
                    )}
                    
                    {selectedVessel && selectedVessel.mmsi === myVesselMmsi && hasMyVesselAlerts && (
                        <div style={{ padding: '12px', textAlign: 'center', color: '#666', fontSize: '12px' }}>
                            Уведомления для вашего судна показаны выше
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default AlertsPanel;