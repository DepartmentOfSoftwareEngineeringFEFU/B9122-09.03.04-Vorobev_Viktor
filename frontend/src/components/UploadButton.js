// frontend/src/components/UploadButton.js
import React, { useRef, useState } from 'react';
import axios from 'axios';

function UploadButton({ onUploadComplete }) {
    const fileInputRef = useRef(null);
    const [uploading, setUploading] = useState(false);
    const [message, setMessage] = useState(null);

    const handleUpload = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        setUploading(true);
        setMessage(null);

        try {
            const response = await axios.post('http://127.0.0.1:8000/api/v1/upload/csv', formData, {
                headers: { 
                    'Content-Type': 'multipart/form-data',
                }
            });
            
            setMessage({ type: 'success', text: `Success: ${response.data.message}` });
            if (onUploadComplete) onUploadComplete();
            setTimeout(() => setMessage(null), 5000);
        } catch (error) {
            const errorMsg = error.response?.data?.detail || error.message;
            setMessage({ type: 'error', text: `Error: ${errorMsg}` });
            setTimeout(() => setMessage(null), 5000);
        } finally {
            setUploading(false);
            fileInputRef.current.value = '';
        }
    };

    const triggerFileInput = () => {
        fileInputRef.current.click();
    };

    return (
        <div style={{ position: 'relative' }}>
            <input
                type="file"
                ref={fileInputRef}
                onChange={handleUpload}
                accept=".csv"
                style={{ display: 'none' }}
            />
            <button
                onClick={triggerFileInput}
                disabled={uploading}
                style={{
                    padding: '8px 16px',
                    backgroundColor: '#3b82f6',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: uploading ? 'not-allowed' : 'pointer',
                    fontSize: '14px',
                    fontWeight: 'bold',
                    opacity: uploading ? 0.6 : 1
                }}
            >
                {uploading ? 'Uploading...' : 'Загрузить CSV'}
            </button>
            
            {message && (
                <div style={{
                    position: 'absolute',
                    top: '100%',
                    right: 0,
                    marginTop: '8px',
                    padding: '8px 12px',
                    backgroundColor: message.type === 'success' ? '#10b981' : '#ef4444',
                    color: 'white',
                    borderRadius: '6px',
                    fontSize: '12px',
                    whiteSpace: 'nowrap',
                    zIndex: 1000
                }}>
                    {message.text}
                </div>
            )}
        </div>
    );
}

export default UploadButton;