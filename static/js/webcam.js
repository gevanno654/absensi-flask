/**
 * Webcam Manager - Mengelola akses kamera dan capture
 */

class WebcamManager {
    constructor(videoElementId, canvasElementId) {
        this.videoElement = document.getElementById(videoElementId);
        
        // Handle canvas element
        if (canvasElementId) {
            this.canvasElement = document.getElementById(canvasElementId);
            if (!this.canvasElement) {
                this.canvasElement = document.createElement('canvas');
                this.canvasElement.id = canvasElementId;
                this.canvasElement.style.display = 'none';
                document.body.appendChild(this.canvasElement);
            }
        } else {
            this.canvasElement = document.createElement('canvas');
            this.canvasElement.id = 'webcam-canvas-' + Date.now();
            this.canvasElement.style.display = 'none';
            document.body.appendChild(this.canvasElement);
        }
        
        this.stream = null;
        this.isActive = false;
        this.cameraDevices = [];
        this.currentDeviceId = null;
        
        // Initialize
        this.init();
    }

    // Initialize webcam manager
    async init() {
        try {
            await this.loadCameraDevices();
            this.setupEventListeners();
        } catch (error) {
            console.error('Failed to initialize webcam:', error);
            throw error;
        }
    }

    // Check if browser supports getUserMedia
    static isSupported() {
        // Check for various browser implementations
        const mediaDevices = navigator.mediaDevices;
        const getUserMedia = navigator.mediaDevices?.getUserMedia || 
                            navigator.webkitGetUserMedia || 
                            navigator.mozGetUserMedia || 
                            navigator.msGetUserMedia;
        
        return !!(getUserMedia && mediaDevices);
    }

    // Get camera permission status
    static async getPermissionStatus() {
        try {
            if (navigator.permissions && navigator.permissions.query) {
                const permissions = await navigator.permissions.query({ name: 'camera' });
                return permissions.state;
            }
            return 'prompt';
        } catch (error) {
            return 'unknown';
        }
    }

    // Load available camera devices
    async loadCameraDevices() {
        try {
            // Check if mediaDevices is available
            if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
                console.warn('Media Devices API not supported');
                this.cameraDevices = [];
                return [];
            }
            
            const devices = await navigator.mediaDevices.enumerateDevices();
            this.cameraDevices = devices.filter(device => device.kind === 'videoinput');
            return this.cameraDevices;
        } catch (error) {
            console.error('Error loading camera devices:', error);
            return [];
        }
    }

    // Update camera select dropdown
    updateCameraSelect(selectElementId) {
        const selectElement = document.getElementById(selectElementId);
        if (!selectElement) return;

        // Clear existing options
        selectElement.innerHTML = '<option value="">Pilih kamera...</option>';

        // Add camera options
        this.cameraDevices.forEach((device, index) => {
            const option = document.createElement('option');
            option.value = device.deviceId;
            option.text = device.label || `Kamera ${index + 1}`;
            selectElement.appendChild(option);
        });

        // Set default to first camera if available
        if (this.cameraDevices.length > 0) {
            this.currentDeviceId = this.cameraDevices[0].deviceId;
            selectElement.value = this.currentDeviceId;
        }
    }

    // Start camera stream with fallback for older browsers
    async start(deviceId = null) {
        try {
            // Stop existing stream if any
            if (this.isActive) {
                await this.stop();
            }

            // Get device ID
            const targetDeviceId = deviceId || this.currentDeviceId;

            // Constraints for video
            const constraints = {
                video: {
                    deviceId: targetDeviceId ? { exact: targetDeviceId } : undefined,
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: 'user'
                },
                audio: false
            };

            // Get media stream with fallback for older browsers
            let stream;
            if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                stream = await navigator.mediaDevices.getUserMedia(constraints);
            } else if (navigator.webkitGetUserMedia) {
                stream = await new Promise((resolve, reject) => {
                    navigator.webkitGetUserMedia(constraints, resolve, reject);
                });
            } else if (navigator.mozGetUserMedia) {
                stream = await new Promise((resolve, reject) => {
                    navigator.mozGetUserMedia(constraints, resolve, reject);
                });
            } else {
                throw new Error('getUserMedia not supported in this browser');
            }
            
            this.stream = stream;
            
            // Set video source
            this.videoElement.srcObject = this.stream;
            
            // Wait for video to be ready
            await new Promise((resolve, reject) => {
                this.videoElement.onloadedmetadata = () => {
                    this.videoElement.play().then(resolve).catch(reject);
                };
                this.videoElement.onerror = reject;
                
                // Timeout after 5 seconds
                setTimeout(() => reject(new Error('Camera timeout')), 5000);
            });

            this.isActive = true;
            this.currentDeviceId = targetDeviceId;
            
            return true;
        } catch (error) {
            console.error('Error starting camera:', error);
            
            // Provide user-friendly error message
            let userMessage = 'Gagal mengakses kamera. ';
            
            if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
                userMessage += 'Izin kamera ditolak. Silakan izinkan akses kamera di pengaturan browser.';
            } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
                userMessage += 'Kamera tidak ditemukan.';
            } else if (error.name === 'NotSupportedError') {
                userMessage += 'Browser tidak mendukung akses kamera.';
            } else if (error.name === 'NotReadableError' || error.name === 'TrackStartError') {
                userMessage += 'Kamera sedang digunakan oleh aplikasi lain.';
            } else {
                userMessage += `Error: ${error.message}`;
            }
            
            throw new Error(userMessage);
        }
    }

    // Stop camera stream
    stop() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => {
                track.stop();
            });
            this.stream = null;
        }
        
        if (this.videoElement) {
            this.videoElement.srcObject = null;
        }
        
        this.isActive = false;
    }

    // Simple capture function
    capture(format = 'jpeg', quality = 0.8) {
        if (!this.isActive || !this.videoElement.videoWidth) {
            throw new Error('Camera is not active or not ready');
        }

        try {
            // Set canvas dimensions
            this.canvasElement.width = this.videoElement.videoWidth;
            this.canvasElement.height = this.videoElement.videoHeight;

            // Draw video frame to canvas
            const context = this.canvasElement.getContext('2d');
            context.drawImage(
                this.videoElement, 
                0, 0, 
                this.canvasElement.width, 
                this.canvasElement.height
            );

            // Convert to data URL
            const mimeType = format === 'png' ? 'image/png' : 'image/jpeg';
            return this.canvasElement.toDataURL(mimeType, quality);
            
        } catch (error) {
            console.error('Error capturing image:', error);
            throw error;
        }
    }

    // Setup event listeners
    setupEventListeners() {
        // Handle page visibility change
        document.addEventListener('visibilitychange', () => {
            if (document.hidden && this.isActive) {
                this.videoElement.pause();
            } else if (!document.hidden && this.isActive) {
                this.videoElement.play().catch(console.error);
            }
        });
    }

    // Switch camera
    async switchCamera(deviceId) {
        if (this.currentDeviceId === deviceId) return;
        
        try {
            await this.start(deviceId);
            this.currentDeviceId = deviceId;
            return true;
        } catch (error) {
            console.error('Error switching camera:', error);
            throw error;
        }
    }

    // Get browser compatibility info
    static getBrowserInfo() {
        return {
            userAgent: navigator.userAgent,
            platform: navigator.platform,
            mediaDevices: !!navigator.mediaDevices,
            getUserMedia: !!(navigator.mediaDevices?.getUserMedia || 
                           navigator.webkitGetUserMedia || 
                           navigator.mozGetUserMedia || 
                           navigator.msGetUserMedia),
            isSecureContext: window.isSecureContext,
            protocol: window.location.protocol,
            host: window.location.host
        };
    }
}

// Make WebcamManager available globally
window.WebcamManager = WebcamManager;