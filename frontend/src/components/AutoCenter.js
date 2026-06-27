// frontend/src/components/AutoCenter.js
import { useEffect } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';

function AutoCenter({ vessels, hasCentered, setHasCentered }) {
    const map = useMap();
    
    useEffect(() => {
        if (!hasCentered && vessels.length > 0) {
            const validVessels = vessels.filter(v => 
                v.latitude && v.longitude && 
                Math.abs(v.latitude) > 0.01 && Math.abs(v.longitude) > 0.01
            );
            if (validVessels.length > 0) {
                const bounds = L.latLngBounds(validVessels.map(v => [v.latitude, v.longitude]));
                map.fitBounds(bounds, { padding: [50, 50] });
                setHasCentered(true);
            }
        }
    }, [vessels, map, hasCentered, setHasCentered]);
    
    return null;
}

export default AutoCenter;