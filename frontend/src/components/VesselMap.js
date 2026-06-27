import React, { useEffect, useState, useCallback } from 'react';
import { MapContainer, TileLayer, Marker, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import axios from 'axios';
import AutoCenter from './AutoCenter';

const getAuthHeaders = () => {
    return {};
};

function ZoomHandler({ setIconSize }) {
    const map = useMap();
    
    useEffect(() => {
        const handleZoom = () => {
            const zoom = map.getZoom();
            const size = Math.min(35, Math.max(3, zoom * 1.7));
            setIconSize(size);
        };
        
        map.on('zoomend', handleZoom);
        handleZoom();
        
        return () => {
            map.off('zoomend', handleZoom);
        };
    }, [map, setIconSize]);
    
    return null;
}

function VesselArrow({ position, course, isMyVessel }) {
    const map = useMap();
    const [rotation, setRotation] = useState(0);
    
    useEffect(() => {
        if (course !== undefined && course !== null) {
            setRotation(course);
        }
    }, [course]);
    
    if (!course) return null;
    
    const arrowColor = isMyVessel ? '#10b981' : '#4470ff';
    
    const arrowIcon = new L.DivIcon({
        html: `<div style="
            transform: rotate(${rotation}deg);
            font-size: 15px;
            font-weight: bold;
            color: ${arrowColor};
            background: transparent;
            text-shadow: 0 0 1px white;
            line-height: 1;
        ">➤</div>`,
        iconSize: [12, 12],
        iconAnchor: [6, 6],
        className: 'vessel-arrow'
    });
    
    return <Marker position={position} icon={arrowIcon} />;
}

const getCustomIcon = (size, isMyVessel = false) => {
    if (isMyVessel) {
        return new L.Icon({
            iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png',
            shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
            iconSize: [size, size * 1.64],
            iconAnchor: [size / 2, size * 1.64],
            popupAnchor: [1, -size],
            shadowSize: [size, size * 1.64]
        });
    }
    
    return new L.Icon({
        iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
        iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
        iconSize: [size, size * 1.64],
        iconAnchor: [size / 2, size * 1.64],
        popupAnchor: [1, -size],
        shadowSize: [size, size * 1.64]
    });
};

function FilterPanel({ filterType, setFilterType }) {
    const vesselTypes = [
        { value: "all", label: "Все суда" },
        { value: "tanker", label: "Танкеры" },
        { value: "container", label: "Контейнеровозы" },
        { value: "passenger", label: "Пассажирские" },
        { value: "tug", label: "Буксиры" },
        { value: "fishing", label: "Рыболовные" },
        { value: "cargo", label: "Грузовые" },
        { value: "wig", label: "Экранопланы" },
        { value: "hsc", label: "Скоростные суда" },
        { value: "military", label: "Военные" },
        { value: "sailing", label: "Парусные" },
        { value: "pleasure", label: "Прогулочные" },
        { value: "pilot", label: "Лоцманские" },
        { value: "sar", label: "Спасательные" },
        { value: "dredger", label: "Земснаряды" },
        { value: "diving", label: "Водолазные" },
        { value: "fire", label: "Пожарные" },
        { value: "port_tender", label: "Портовые" },
        { value: "other", label: "Другие" }
    ];
    
    return (
        <div style={{
            position: 'absolute',
            top: 12,
            right: 350,
            zIndex: 1000,
            background: 'white',
            padding: '4px 8px',
            borderRadius: '6px',
            boxShadow: '0 1px 4px rgba(0,0,0,0.2)',
            fontSize: '13px'
        }}>
            <select 
                value={filterType} 
                onChange={(e) => setFilterType(e.target.value)}
                style={{
                    padding: '4px 6px',
                    borderRadius: '4px',
                    border: '1px solid #ccc',
                    fontSize: '12px',
                    cursor: 'pointer'
                }}
            >
                {vesselTypes.map(type => (
                    <option key={type.value} value={type.value}>
                        {type.label}
                    </option>
                ))}
            </select>
        </div>
    );
}

const calculateDistance = (lat1, lon1, lat2, lon2) => {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
};

const findNearestPointOnRoute = (route, currentLat, currentLon) => {
    if (!route || route.length === 0) return null;
    
    let minDist = Infinity;
    let nearestIndex = 0;
    
    for (let i = 0; i < route.length; i++) {
        const point = route[i];
        const dist = calculateDistance(currentLat, currentLon, point[0], point[1]);
        if (dist < minDist) {
            minDist = dist;
            nearestIndex = i;
        }
    }
    
    return { index: nearestIndex, point: route[nearestIndex], distance: minDist };
};

const findPointNearPort = (route, portLat, portLon) => {
    if (!route || route.length === 0) return null;
    
    let minDist = Infinity;
    let nearestIndex = route.length - 1;
    
    for (let i = 0; i < route.length; i++) {
        const point = route[i];
        const dist = calculateDistance(portLat, portLon, point[0], point[1]);
        if (dist < minDist) {
            minDist = dist;
            nearestIndex = i;
        }
    }
    
    return { index: nearestIndex, point: route[nearestIndex], distance: minDist };
};

const getRouteToPort = (route, currentLat, currentLon, portLat, portLon) => {
    if (!route || route.length === 0) return [];
    
    const nearestToCurrent = findNearestPointOnRoute(route, currentLat, currentLon);
    if (!nearestToCurrent) return [];
    
    const nearestToPort = findPointNearPort(route, portLat, portLon);
    if (!nearestToPort) return route.slice(nearestToCurrent.index);
    
    if (nearestToPort.index <= nearestToCurrent.index) {
        return route.slice(nearestToCurrent.index);
    }
    
    return route.slice(nearestToCurrent.index, nearestToPort.index + 1);
};

function VesselInfoPanel({ vessel, onClose, routeType, setRouteType, compareMode, setCompareMode, comparisonData }) {
    if (!vessel) return null;
    
    const getVesselTypeName = (type) => {
        if (!type) return 'Не указан';
        
        const lowerType = type.toLowerCase();
        
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
        
        return types[lowerType] || type;
    };

    return (
        <div style={{
            position: 'absolute',
            bottom: 20,
            left: 20,
            zIndex: 1000,
            backgroundColor: 'white',
            borderRadius: '12px',
            boxShadow: '0 4px 20px rgba(0,0,0,0.2)',
            width: '320px',
            maxWidth: '90%',
            overflow: 'hidden'
        }}>
            <div style={{
                backgroundColor: '#1a1a2e',
                color: 'white',
                padding: '12px 16px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
            }}>
                <div>
                    <strong>{vessel.name || 'Без названия'}</strong>
                    <span style={{ fontSize: '11px', marginLeft: '8px', opacity: 0.8 }}>
                        MMSI: {vessel.mmsi}
                    </span>
                </div>
                <button
                    onClick={onClose}
                    style={{
                        background: 'rgba(255,255,255,0.2)',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '16px',
                        color: 'white',
                        padding: '4px 8px',
                        transition: 'background 0.2s'
                    }}
                    onMouseEnter={(e) => e.target.style.background = 'rgba(255,255,255,0.3)'}
                    onMouseLeave={(e) => e.target.style.background = 'rgba(255,255,255,0.2)'}
                    title="Закрыть"
                >
                    ✕
                </button>
            </div>
            
            <div style={{ padding: '12px 16px', borderBottom: '1px solid #eee' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '13px' }}>
                    <div>
                        <div style={{ color: '#666', fontSize: '11px' }}>Тип судна</div>
                        <div>{getVesselTypeName(vessel.vessel_type)}</div>
                    </div>
                    <div>
                        <div style={{ color: '#666', fontSize: '11px' }}>Скорость</div>
                        <div>{vessel.speed ? `${vessel.speed.toFixed(1)} уз` : '—'}</div>
                    </div>
                    <div>
                        <div style={{ color: '#666', fontSize: '11px' }}>Курс</div>
                        <div>{vessel.course ? `${vessel.course.toFixed(0)}°` : '—'}</div>
                    </div>
                    <div>
                        <div style={{ color: '#666', fontSize: '11px' }}>Позиция</div>
                        <div>{vessel.latitude?.toFixed(4)}°, {vessel.longitude?.toFixed(4)}°</div>
                    </div>
                </div>
            </div>
            
            <div style={{ padding: '12px 16px', borderBottom: '1px solid #eee' }}>
                <div style={{ fontSize: '13px', fontWeight: 'bold', marginBottom: '8px' }}>
                    Тип маршрута
                </div>
                <select 
                    value={routeType} 
                    onChange={(e) => setRouteType(e.target.value)}
                    style={{ 
                        padding: '6px 10px', 
                        borderRadius: '6px', 
                        cursor: 'pointer', 
                        width: '100%',
                        border: '1px solid #ddd',
                        fontSize: '13px'
                    }}
                >
                    <option value="historical">Эмпирическая траектория</option>
                    <option value="optimal">Оптимальная траектория</option>
                </select>
            </div>
            
            <div style={{ padding: '12px 16px', borderBottom: '1px solid #eee' }}>
                <label style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '8px', 
                    cursor: 'pointer',
                    fontSize: '13px'
                }}>
                    <input 
                        type="checkbox" 
                        checked={compareMode} 
                        onChange={(e) => setCompareMode(e.target.checked)}
                    />
                    <span>Сравнить маршруты</span>
                </label>
            </div>
            
            {compareMode && comparisonData && (
                <div style={{ padding: '12px 16px', backgroundColor: '#f8f9fa' }}>
                    <div style={{ fontSize: '13px', fontWeight: 'bold', marginBottom: '8px' }}>
                        Сравнение маршрутов
                    </div>
                    <div style={{ fontSize: '12px' }}>
                        <div style={{ marginBottom: '8px' }}>
                            <div style={{ color: '#f59e0b', fontWeight: 'bold' }}>Эмпирическая траектория:</div>
                            <div>Расстояние: {comparisonData.historicalDistance} км</div>
                            <div>Время в пути: {comparisonData.historicalTime} мин</div>
                        </div>
                        <div style={{ marginBottom: '8px' }}>
                            <div style={{ color: '#10b981', fontWeight: 'bold' }}>Оптимальная траектория:</div>
                            <div>Расстояние: {comparisonData.optimalDistance} км</div>
                            <div>Время в пути: {comparisonData.optimalTime} мин</div>
                        </div>
                        <div style={{ borderTop: '1px solid #ddd', paddingTop: '8px', marginTop: '4px' }}>
                            <div>Разница: {comparisonData.difference} км ({comparisonData.differencePercent}%)</div>
                            {comparisonData.savings > 0 ? (
                                <div style={{ color: '#10b981' }}>Экономия времени: {comparisonData.savings} мин</div>
                            ) : comparisonData.savings < 0 ? (
                                <div style={{ color: '#ef4444' }}>Длиннее на {Math.abs(comparisonData.savings)} мин</div>
                            ) : (
                                <div style={{ color: '#666' }}>Маршруты равны</div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

function VesselMap({ onVesselSelect }) {
    const [vessels, setVessels] = useState([]);
    const [positions, setPositions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedVessel, setSelectedVessel] = useState(null);
    const [error, setError] = useState(null);
    const [iconSize, setIconSize] = useState(30);
    const [filterType, setFilterType] = useState('all');
    const [routeType, setRouteType] = useState('direct');
    const [historicalRouteData, setHistoricalRouteData] = useState([]);
    const [routes, setRoutes] = useState({ 
        historical: [], 
        historicalToPort: [],
        optimal: [] 
    });
    const [compareMode, setCompareMode] = useState(false);
    const [comparisonRoutes, setComparisonRoutes] = useState({ direct: [], historical: [] });
    const [hasCentered, setHasCentered] = useState(false);
    const [destinationPort, setDestinationPort] = useState(null);
    const [myVesselMmsi, setMyVesselMmsi] = useState(null);
    const [comparisonData, setComparisonData] = useState({
        directDistance: 0,
        historicalDistance: 0,
        difference: 0,
        differencePercent: 0,
        directTime: 0,
        historicalTime: 0,
        savings: 0
    });



    const closeVesselPanel = () => {
        setSelectedVessel(null);
        if (onVesselSelect) onVesselSelect(null);
        setRoutes({ direct: [], historical: [], historicalToPort: [], optimal: [] });
        setComparisonRoutes({ direct: [], historical: [] });
        setCompareMode(false);
        setDestinationPort(null);
    };

    const calculateDistanceFn = (lat1, lon1, lat2, lon2) => {
        const R = 6371;
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                  Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                  Math.sin(dLon/2) * Math.sin(dLon/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    };

    const calculateRouteDistance = (route) => {
        if (!route || route.length < 2) return 0;
        let total = 0;
        for (let i = 1; i < route.length; i++) {
            total += calculateDistanceFn(route[i-1][0], route[i-1][1], route[i][0], route[i][1]);
        }
        return Math.round(total * 10) / 10;
    };

    const calculateTravelTime = (distance) => {
        const speedKmh = 18.5;
        const timeHours = distance / speedKmh;
        return Math.round(timeHours * 60);
    };

    const updateComparisonData = useCallback((historicalRoute, optimalRoute) => {
        if (!historicalRoute || !optimalRoute) {
            return;
        }
        
        const historicalDist = calculateRouteDistance(historicalRoute);
        const optimalDist = calculateRouteDistance(optimalRoute);
        const diff = Math.abs(historicalDist - optimalDist);
        const diffPercent = optimalDist > 0 ? Math.round((diff / optimalDist) * 100) : 0;
        const historicalTime = calculateTravelTime(historicalDist);
        const optimalTime = calculateTravelTime(optimalDist);
        const savings = historicalTime - optimalTime; 
        
        console.log('Comparison data:', {
            historicalDist,
            optimalDist,
            historicalTime,
            optimalTime
        });
        
        setComparisonData({
            historicalDistance: historicalDist,
            optimalDistance: optimalDist,
            difference: diff,
            differencePercent: diffPercent,
            historicalTime: historicalTime,
            optimalTime: optimalTime,
            savings: savings
        });
    }, []);

    const loadRoutes = useCallback(async (vessel) => {
        if (!vessel) return;
        
        try {
            const headers = getAuthHeaders();
            
            let port = null;
            if (vessel.destination_lat && vessel.destination_lon) {
                const portRes = await axios.get(`http://127.0.0.1:8000/api/v1/routes/ports/near`, {
                    params: { lat: vessel.destination_lat, lon: vessel.destination_lon }
                });
                port = portRes.data;
                setDestinationPort(port);
            }
            
            const historicalRes = await axios.get(`http://127.0.0.1:8000/api/v1/routes/historical?mmsi=${vessel.mmsi}`, { headers });
            
            const historicalRoute = historicalRes.data.route || [];
            
            setRoutes(prev => ({
                ...prev,
                historical: historicalRoute,
                historicalToPort: port ? getRouteToPort(
                    historicalRoute,
                    vessel.latitude,
                    vessel.longitude,
                    port.latitude,
                    port.longitude
                ) : historicalRoute
            }));
            
            setHistoricalRouteData(historicalRoute);
            
        } catch (err) {
            console.error('Ошибка загрузки исторического маршрута:', err);
            setRoutes(prev => ({ ...prev, historical: [], historicalToPort: [] }));
        }
    }, []);

    // Загрузка маршрутов для сравнения
    const loadComparison = useCallback(async (vessel) => {
        if (!vessel) return;
        
        const headers = getAuthHeaders();
        
        if (!vessel.destination_lat || !vessel.destination_lon) {
            console.log('Нет данных о пункте назначения для судна', vessel.mmsi);
            return;
        }
        
        try {
            const directRes = await axios.get(`http://127.0.0.1:8000/api/v1/routes/direct_simple`, { 
                params: {
                    start_lat: vessel.latitude,
                    start_lon: vessel.longitude,
                    end_lat: vessel.destination_lat,
                    end_lon: vessel.destination_lon,
                },
                headers
            });
            
            const historicalRes = await axios.get(`http://127.0.0.1:8000/api/v1/routes/historical`, {
                params: { mmsi: vessel.mmsi },
                headers
            });
            
            const directRoute = directRes.data.route || [];
            const historicalRoute = historicalRes.data.route || [];
            
            setComparisonRoutes({
                direct: directRoute,
                historical: historicalRoute
            });
            
            updateComparisonData(directRoute, historicalRoute);
        } catch (err) {
            console.error('Ошибка загрузки для сравнения:', err);
        }
    }, [updateComparisonData]);

    const loadOptimalRoute = useCallback(async (historicalWaypoints) => {
        if (!historicalWaypoints || historicalWaypoints.length === 0) return;
        
        try {
            const headers = getAuthHeaders();
            const response = await axios.post(`http://127.0.0.1:8000/api/v1/routes/optimize`, {
                waypoints: historicalWaypoints
            }, { headers });
            
            const optimalRouteData = response.data.route || [];
            
            setRoutes(prev => ({
                ...prev,
                optimal: optimalRouteData
            }));
            
            // Обновляем сравнение
            if (historicalWaypoints.length > 0) {
                updateComparisonData(historicalWaypoints, optimalRouteData);
            }
        } catch (err) {
            console.error('Ошибка оптимизации маршрута:', err);
            setRoutes(prev => ({ ...prev, optimal: historicalWaypoints })); 
        }
    }, [updateComparisonData]);

    const handleMarkerClick = useCallback(async (vessel) => {
        if (selectedVessel?.mmsi === vessel.mmsi) {
            setSelectedVessel(null);
            if (onVesselSelect) onVesselSelect(null);
            setRoutes({ historical: [], historicalToPort: [], optimal: [] });
            setCompareMode(false);
            setDestinationPort(null);
        } else {
            const vesselWithCoords = {
                ...vessel,
                latitude: vessel.latitude,
                longitude: vessel.longitude
            };
            setSelectedVessel(vesselWithCoords);
            if (onVesselSelect) onVesselSelect(vesselWithCoords);
            
            setRouteType('historical');
            setRoutes({ historical: [], historicalToPort: [], optimal: [] });
            
            const headers = getAuthHeaders();
            
            try {
                let port = null;
                if (vessel.destination_lat && vessel.destination_lon) {
                    const portRes = await axios.get(`http://127.0.0.1:8000/api/v1/routes/ports/near`, {
                        params: { lat: vessel.destination_lat, lon: vessel.destination_lon },
                        headers
                    });
                    port = portRes.data;
                    setDestinationPort(port);
                }
                
                const historicalRes = await axios.get(`http://127.0.0.1:8000/api/v1/routes/historical?mmsi=${vessel.mmsi}`, { headers });
                const fullHistoricalRoute = historicalRes.data.route || [];
                
                let historicalRoute = fullHistoricalRoute;
                if (port && fullHistoricalRoute.length > 0) {
                    historicalRoute = getRouteToPort(
                        fullHistoricalRoute,
                        vessel.latitude,
                        vessel.longitude,
                        port.latitude,
                        port.longitude
                    );
                }
                
                setRoutes(prev => ({
                    ...prev,
                    historical: historicalRoute,
                    historicalToPort: historicalRoute
                }));
                
                if (historicalRoute.length > 0) {
                    await loadOptimalRoute(historicalRoute);
                }
                
            } catch (err) {
                console.error('Ошибка загрузки маршрутов:', err);
            }
        }
    }, [selectedVessel, onVesselSelect, loadOptimalRoute]);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [vesselsRes, positionsRes] = await Promise.all([
                    axios.get('http://127.0.0.1:8000/api/v1/vessels/'),
                    axios.get('http://127.0.0.1:8000/api/v1/positions/latest')
                ]);
                
                setVessels(Array.isArray(vesselsRes.data) ? vesselsRes.data : []);
                setPositions(Array.isArray(positionsRes.data) ? positionsRes.data : []);
                setLoading(false);
            } catch (err) {
                console.error('Ошибка загрузки:', err);
                setError(err.message);
                setLoading(false);
            }
        };
        
        fetchData();
    }, []);

    const vesselsWithPositions = vessels
        .map(vessel => {
            const pos = positions.find(p => p.mmsi === vessel.mmsi);
            if (!pos) return null;
            return {
                ...vessel,
                latitude: pos.latitude,
                longitude: pos.longitude,
                speed: pos.speed || 0,
                course: pos.course || 0,
            };
        })
        .filter(v => v !== null);

    const filteredVessels = vesselsWithPositions.filter(vessel => {
        if (filterType === 'all') return true;
        return vessel.vessel_type?.toLowerCase() === filterType.toLowerCase();
    });

    const checkVesselAlerts = async (vessel) => {
        try {
            const headers = getAuthHeaders();
            await axios.post(`http://127.0.0.1:8000/api/v1/alerts/check`, {
                mmsi: vessel.mmsi,
                latitude: vessel.latitude,
                longitude: vessel.longitude,
                speed: vessel.speed,
                course: vessel.course,  
                vessel_type: vessel.vessel_type
            }, { headers });
        } catch (err) {
            console.error('Ошибка проверки:', err);
        }
    };

    const center = [43.115, 131.885];

    if (loading) return <div style={{ padding: '20px', textAlign: 'center' }}>Загрузка карты...</div>;
    if (error) return <div style={{ padding: '20px', textAlign: 'center', color: 'red' }}>Ошибка: {error}</div>;

    return (
        <MapContainer center={center} zoom={13} style={{ height: '100%', width: '100%' }}>
            <AutoCenter vessels={filteredVessels} hasCentered={hasCentered} setHasCentered={setHasCentered} />
            <ZoomHandler setIconSize={setIconSize} />
            <FilterPanel filterType={filterType} setFilterType={setFilterType} />
                        
            <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution=""
            />

            {/* Исторический маршрут */}
            {routes.historical && routes.historical.length > 0 && routeType === 'historical' && (
                <>
                    <Polyline 
                        positions={routes.historical} 
                        color="#f59e0b" 
                        weight={4} 
                        opacity={0.4}
                        dashArray="8, 8"
                    />
                    
                    {routes.historicalToPort && routes.historicalToPort.length > 1 && (
                        <Polyline 
                            positions={routes.historicalToPort} 
                            color="#f59e0b" 
                            weight={5} 
                            opacity={0.95}
                        />
                    )}
                </>
            )}
            
            {routes.optimal && routes.optimal.length > 0 && routeType === 'optimal' && (
                <Polyline 
                    positions={routes.optimal} 
                    color="#10b981" 
                    weight={5} 
                    opacity={0.9}
                />
            )}
            
            {compareMode && (
                <>
                    {routes.historical && routes.historical.length > 0 && (
                        <Polyline 
                            positions={routes.historical} 
                            color="#f59e0b" 
                            weight={4} 
                            opacity={0.7}
                            dashArray="5, 5"
                        />
                    )}
                    {routes.optimal && routes.optimal.length > 0 && (
                        <Polyline 
                            positions={routes.optimal} 
                            color="#10b981" 
                            weight={4} 
                            opacity={0.7}
                            dashArray="5, 5"
                        />
                    )}
                </>
            )}
            
            {filteredVessels.map((vessel) => {
                const isMyVessel = myVesselMmsi === vessel.mmsi;
                const icon = getCustomIcon(iconSize, isMyVessel);
                
                return (
                    <React.Fragment key={vessel.mmsi}>
                        <Marker 
                            position={[vessel.latitude, vessel.longitude]}
                            icon={icon}
                            eventHandlers={{
                                click: () => handleMarkerClick(vessel),
                            }}
                        />
                        {vessel.course !== undefined && vessel.course !== null && vessel.course > 0 && (
                            <VesselArrow 
                                position={[vessel.latitude, vessel.longitude]} 
                                course={vessel.course}
                                isMyVessel={isMyVessel}
                            />
                        )}
                    </React.Fragment>
                );
            })}

            <VesselInfoPanel 
                vessel={selectedVessel}
                onClose={closeVesselPanel}
                routeType={routeType}
                setRouteType={setRouteType}
                compareMode={compareMode}
                setCompareMode={setCompareMode}
                comparisonData={comparisonData}
            />

        </MapContainer>
    );
}

export default VesselMap;