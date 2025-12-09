/**
 * Main JavaScript File - Sistem Absensi Wajah
 * Fungsi umum dan utilitas
 */

// Global variables
let API_BASE_URL = window.location.origin;

// Utility functions
const Utils = {
    // Format date
    formatDate: (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('id-ID', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    },

    // Format time
    formatTime: (timeString) => {
        return new Date(`1970-01-01T${timeString}`).toLocaleTimeString('id-ID', {
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    // Format datetime
    formatDateTime: (dateTimeString) => {
        const date = new Date(dateTimeString);
        return date.toLocaleString('id-ID', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    // Show notification
    showNotification: (message, type = 'info', duration = 3000) => {
        // Remove existing notifications
        const existingNotifications = document.querySelectorAll('.custom-notification');
        existingNotifications.forEach(notification => notification.remove());

        // Create notification element
        const notification = document.createElement('div');
        notification.className = `custom-notification alert alert-${type} alert-dismissible fade show`;
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        // Style the notification
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
            max-width: 500px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        `;

        // Add to document
        document.body.appendChild(notification);

        // Auto remove after duration
        if (duration > 0) {
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, duration);
        }
    },

    // Confirm dialog
    confirmDialog: (message, callback) => {
        const modalHtml = `
            <div class="modal fade" id="confirmModal" tabindex="-1">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Konfirmasi</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p>${message}</p>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Batal</button>
                            <button type="button" class="btn btn-primary" id="confirmButton">Ya, Lanjutkan</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal
        const existingModal = document.getElementById('confirmModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Add new modal
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
        modal.show();

        // Handle confirm button click
        document.getElementById('confirmButton').addEventListener('click', () => {
            modal.hide();
            if (typeof callback === 'function') {
                callback();
            }
        });
    },

    // Loading overlay
    showLoading: (message = 'Memproses...') => {
        // Remove existing loading
        const existingLoading = document.getElementById('loadingOverlay');
        if (existingLoading) {
            existingLoading.remove();
        }

        // Create loading element
        const loadingHtml = `
            <div id="loadingOverlay" class="loading-overlay">
                <div class="loading-content">
                    <div class="spinner-border text-primary" style="width: 3rem; height: 3rem;" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="mt-3">${message}</p>
                </div>
            </div>
        `;

        // Add to document
        document.body.insertAdjacentHTML('beforeend', loadingHtml);
    },

    hideLoading: () => {
        const loadingOverlay = document.getElementById('loadingOverlay');
        if (loadingOverlay) {
            loadingOverlay.remove();
        }
    },

    // Validate NIM
    validateNIM: (nim) => {
        return /^[0-9]{10,15}$/.test(nim);
    },

    // Validate name
    validateName: (name) => {
        return name.length >= 2 && name.length <= 100;
    }
};

// API Service
const APIService = {
    // GET request
    get: async (endpoint) => {
        try {
            const response = await fetch(`${API_BASE_URL}${endpoint}`);
            return await response.json();
        } catch (error) {
            console.error('GET request failed:', error);
            return { success: false, message: 'Network error' };
        }
    },

    // POST request
    post: async (endpoint, data) => {
        try {
            const response = await fetch(`${API_BASE_URL}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            return await response.json();
        } catch (error) {
            console.error('POST request failed:', error);
            return { success: false, message: 'Network error' };
        }
    },

    // Check system status
    checkSystemStatus: async () => {
        return await APIService.get('/api/system/status');
    }
};

// Attendance Manager
const AttendanceManager = {
    // Get today's attendance
    getTodayAttendance: async () => {
        return await APIService.get('/api/attendance/today');
    },

    // Get attendance by date
    getAttendanceByDate: async (date) => {
        return await APIService.get(`/api/attendance/date/${date}`);
    },

    // Get statistics
    getStatistics: async () => {
        return await APIService.get('/api/stats');
    },

    // Get students list
    getStudents: async () => {
        return await APIService.get('/api/students');
    },

    // Register student
    registerStudent: async (nim, name, imageData) => {
        return await APIService.post('/api/register', {
            nim: nim,
            name: name,
            image: imageData
        });
    },

    // Recognize face
    recognizeFace: async (imageData) => {
        return await APIService.post('/api/recognize', {
            image: imageData
        });
    }
};

// Data Exporter
const DataExporter = {
    // Export to CSV
    exportToCSV: (data, filename = 'data.csv') => {
        if (!data || data.length === 0) {
            Utils.showNotification('Tidak ada data untuk diexport', 'warning');
            return;
        }

        // Convert data to CSV
        const headers = Object.keys(data[0]);
        const csvRows = [
            headers.join(','),
            ...data.map(row => 
                headers.map(header => {
                    const cell = row[header];
                    return typeof cell === 'string' && cell.includes(',') ? 
                        `"${cell}"` : cell;
                }).join(',')
            )
        ];

        const csvString = csvRows.join('\n');
        const blob = new Blob([csvString], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        
        // Create download link
        const a = document.createElement('a');
        a.setAttribute('hidden', '');
        a.setAttribute('href', url);
        a.setAttribute('download', filename);
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        Utils.showNotification(`Data berhasil diexport ke ${filename}`, 'success');
    },

    // Export to JSON
    exportToJSON: (data, filename = 'data.json') => {
        const jsonString = JSON.stringify(data, null, 2);
        const blob = new Blob([jsonString], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.setAttribute('hidden', '');
        a.setAttribute('href', url);
        a.setAttribute('download', filename);
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        Utils.showNotification(`Data berhasil diexport ke ${filename}`, 'success');
    }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Add CSS for custom components
    const style = document.createElement('style');
    style.textContent = `
        .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 99999;
        }
        
        .loading-content {
            background: white;
            padding: 30px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }
        
        .custom-notification {
            animation: slideInRight 0.3s ease;
        }
        
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        .fade-out {
            animation: fadeOut 0.3s ease forwards;
        }
        
        @keyframes fadeOut {
            from {
                opacity: 1;
            }
            to {
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);

    // Check system status on page load
    APIService.checkSystemStatus().then(status => {
        if (!status.success) {
            Utils.showNotification(
                'Sistem sedang mengalami gangguan. Silakan coba lagi nanti.',
                'danger',
                5000
            );
        }
    });
});

// Make utilities available globally
window.Utils = Utils;
window.APIService = APIService;
window.AttendanceManager = AttendanceManager;
window.DataExporter = DataExporter;