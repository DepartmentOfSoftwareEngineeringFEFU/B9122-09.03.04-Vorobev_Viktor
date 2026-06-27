import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import VesselMap from './components/VesselMap';
import AlertsPanel from './components/AlertsPanel';
import UploadButton from './components/UploadButton';
import AdminPanel from './components/AdminPanel';
import './App.css';

function App() {
    const [selectedVessel, setSelectedVessel] = useState(null);
    const [refreshTrigger, setRefreshTrigger] = useState(0);
    const [showAdminPanel, setShowAdminPanel] = useState(false);

    const handleUploadComplete = () => {
        setRefreshTrigger(prev => prev + 1);
    };

    return (
        <Router>
            <div className="App">
                <Routes>
                    <Route 
                        path="/map" 
                        element={
                            <>
                                <header style={{
                                    backgroundColor: '#1a1a2e',
                                    color: 'white',
                                    padding: '15px 20px',
                                    boxShadow: '0 2px 5px rgba(0,0,0,0.1)',
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center'
                                }}>
                                    <h1 style={{ margin: 0, fontSize: '1.8rem' }}>Система мониторинга судов</h1>
                                    <div style={{ display: 'flex', gap: '15px', alignItems: 'center' }}>
                                        <UploadButton onUploadComplete={handleUploadComplete} />
                                        <button
                                            onClick={() => setShowAdminPanel(true)}
                                            style={{
                                                padding: '6px 12px',
                                                backgroundColor: '#6b7280',
                                                color: 'white',
                                                border: 'none',
                                                borderRadius: '4px',
                                                cursor: 'pointer'
                                            }}
                                        >
                                            Администрация
                                        </button>
                                    </div>
                                </header>
                                <main>
                                    <VesselMap 
                                        key={refreshTrigger}
                                        onVesselSelect={setSelectedVessel} 
                                    />
                                    <AlertsPanel selectedVessel={selectedVessel} />
                                </main>
                            </>
                        } 
                    />
                    <Route path="/" element={<Navigate to="/map" />} />
                </Routes>
                
                {showAdminPanel && <AdminPanel onClose={() => setShowAdminPanel(false)} />}
            </div>
        </Router>
    );
}

export default App;