"use strict";

(function() {
    'use strict';

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function showMessage(message, type) {
        const container = document.getElementById('statusMessage');
        if (!container) return;

        const msg = document.createElement('div');
        msg.className = 'status-message status-message-' + type;
        
        const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        icon.setAttribute('viewBox', '0 0 24 24');
        icon.setAttribute('fill', 'none');
        icon.setAttribute('stroke', 'currentColor');
        icon.setAttribute('stroke-width', '2');
        icon.setAttribute('stroke-linecap', 'round');
        icon.setAttribute('stroke-linejoin', 'round');
        
        if (type === 'success') {
            icon.innerHTML = '<polyline points="20 6 9 17 4 12"></polyline>';
        } else if (type === 'error') {
            icon.innerHTML = '<circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line>';
        } else {
            icon.innerHTML = '<circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line>';
        }
        
        msg.appendChild(icon);
        msg.appendChild(document.createTextNode(message));
        
        container.innerHTML = '';
        container.appendChild(msg);
        
        if (type === 'success') {
            setTimeout(function() {
                if (msg.parentNode) {
                    msg.remove();
                }
            }, 5000);
        }
    }

    function setLoading(element, loading) {
        if (loading) {
            element.disabled = true;
            element.dataset.originalText = element.innerHTML;
            element.innerHTML = '<span class="loading-spinner"></span> Processing...';
        } else {
            element.disabled = false;
            if (element.dataset.originalText) {
                element.innerHTML = element.dataset.originalText;
            }
        }
    }

    function initThemeToggle() {
        const toggle = document.getElementById('themeToggle');
        if (!toggle) return;

        const savedTheme = localStorage.getItem('theme');
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        
        if (savedTheme === 'light' || (!savedTheme && !prefersDark)) {
            document.documentElement.setAttribute('data-theme', 'light');
            updateThemeToggleUI(true);
        }

        toggle.addEventListener('click', function() {
            const isLight = document.documentElement.getAttribute('data-theme') === 'light';
            if (isLight) {
                document.documentElement.removeAttribute('data-theme');
                localStorage.setItem('theme', 'dark');
                updateThemeToggleUI(false);
            } else {
                document.documentElement.setAttribute('data-theme', 'light');
                localStorage.setItem('theme', 'light');
                updateThemeToggleUI(true);
            }
        });

        toggle.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                toggle.click();
            }
        });
    }

    function updateThemeToggleUI(isLight) {
        const toggle = document.getElementById('themeToggle');
        if (!toggle) return;
        
        const span = toggle.querySelector('span');
        const svg = toggle.querySelector('svg');
        
        if (isLight) {
            span.textContent = 'Dark Mode';
            if (svg) {
                svg.innerHTML = '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>';
            }
        } else {
            span.textContent = 'Light Mode';
            if (svg) {
                svg.innerHTML = '<circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>';
            }
        }
    }

    function initUpload() {
        const uploadZone = document.getElementById('uploadZone');
        const fileInput = document.getElementById('fileInput');
        const browseBtn = document.getElementById('browseBtn');
        const changeFileBtn = document.getElementById('changeFileBtn');
        const nextStepBtn = document.getElementById('nextStepBtn');

        if (!uploadZone || !fileInput) return;

        uploadZone.addEventListener('click', function(e) {
            if (e.target !== changeFileBtn) {
                fileInput.click();
            }
        });

        uploadZone.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                fileInput.click();
            }
        });

        if (browseBtn) {
            browseBtn.addEventListener('click', function() {
                fileInput.click();
            });
        }

        if (changeFileBtn) {
            changeFileBtn.addEventListener('click', function() {
                fileInput.click();
            });
        }

        fileInput.addEventListener('change', function(e) {
            if (this.files && this.files[0]) {
                handleFileSelect(this.files[0]);
            }
        });

        uploadZone.addEventListener('dragover', function(e) {
            e.preventDefault();
            e.stopPropagation();
            this.classList.add('drag-over');
        });

        uploadZone.addEventListener('dragleave', function(e) {
            e.preventDefault();
            e.stopPropagation();
            this.classList.remove('drag-over');
        });

        uploadZone.addEventListener('drop', function(e) {
            e.preventDefault();
            e.stopPropagation();
            this.classList.remove('drag-over');
            
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                handleFileSelect(e.dataTransfer.files[0]);
            }
        });

        if (nextStepBtn) {
            nextStepBtn.addEventListener('click', function() {
                window.location.href = '/configure';
            });
        }
    }

    function handleFileSelect(file) {
        const allowedTypes = ['.csv', '.xlsx', '.xls', '.dbf'];
        const fileExt = '.' + file.name.split('.').pop().toLowerCase();
        
        if (!allowedTypes.includes(fileExt)) {
            showMessage('Invalid file type. Please select a CSV, XLSX, XLS, or DBF file.', 'error');
            return;
        }

        if (file.size > 50 * 1024 * 1024) {
            showMessage('File is too large. Maximum size is 50 MB.', 'error');
            return;
        }

        uploadFile(file);
    }

    function uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        const nextBtn = document.getElementById('nextStepBtn');
        if (nextBtn) {
            setLoading(nextBtn, true);
        }

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('fileName').textContent = data.filename;
                document.getElementById('fileSize').textContent = formatFileSize(data.size);
                document.getElementById('fileType').textContent = data.extension.toUpperCase();
                document.getElementById('fileExtBadge').textContent = data.extension.toUpperCase();
                
                document.getElementById('fileInfoSection').classList.remove('hidden');
                document.getElementById('emptyState').classList.add('hidden');
                
                if (nextBtn) {
                    nextBtn.disabled = false;
                    setLoading(nextBtn, false);
                }
                
                showMessage('File uploaded successfully', 'success');
            } else {
                showMessage(data.message || 'Upload failed', 'error');
                if (nextBtn) {
                    setLoading(nextBtn, false);
                }
            }
        })
        .catch(error => {
            console.error('Upload error:', error);
            showMessage('Upload failed. Please try again.', 'error');
            if (nextBtn) {
                setLoading(nextBtn, false);
            }
        });
    }

    function initConfigure() {
        const formatSelector = document.getElementById('formatSelector');
        const convertBtn = document.getElementById('convertBtn');
        const targetFormatDisplay = document.getElementById('targetFormatDisplay');
        const fileDetailsGrid = document.getElementById('fileDetailsGrid');
        const columnList = document.getElementById('columnList');
        const columnItems = document.getElementById('columnItems');
        const loadingDetails = document.getElementById('loadingDetails');

        if (!formatSelector) return;

        formatSelector.addEventListener('change', function(e) {
            if (e.target.name === 'target_format') {
                const selected = formatSelector.querySelector('input[name="target_format"]:checked');
                
                formatSelector.querySelectorAll('.format-option').forEach(function(opt) {
                    opt.classList.remove('selected');
                });
                
                if (selected) {
                    selected.closest('.format-option').classList.add('selected');
                    targetFormatDisplay.textContent = selected.value.toUpperCase();
                    convertBtn.disabled = false;
                }
            }
        });

        formatSelector.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                const option = e.target.closest('.format-option');
                if (option) {
                    const input = option.querySelector('input');
                    if (input) {
                        input.checked = true;
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }
            }
        });

        if (convertBtn) {
            convertBtn.addEventListener('click', function() {
                const selected = formatSelector.querySelector('input[name="target_format"]:checked');
                if (!selected) {
                    showMessage('Please select a target format', 'error');
                    return;
                }

                performConversion(selected.value);
            });
        }

        if (fileDetailsGrid) {
            fetchFileDetails();
        }
    }

    function fetchFileDetails() {
        const fileDetailsGrid = document.getElementById('fileDetailsGrid');
        const loadingDetails = document.getElementById('loadingDetails');
        const columnList = document.getElementById('columnList');
        const columnItems = document.getElementById('columnItems');

        if (loadingDetails) loadingDetails.style.display = 'block';

        fetch('/api/file-info', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: ''
        })
        .then(response => response.json())
        .then(data => {
            if (loadingDetails) loadingDetails.style.display = 'none';

            if (data.success) {
                const info = data.data;
                
                fileDetailsGrid.innerHTML = 
                    '<div class="file-detail-item">' +
                        '<div class="file-detail-label">Rows</div>' +
                        '<div class="file-detail-value">' + info.rows.toLocaleString() + '</div>' +
                    '</div>' +
                    '<div class="file-detail-item">' +
                        '<div class="file-detail-label">Columns</div>' +
                        '<div class="file-detail-value">' + info.columns + '</div>' +
                    '</div>' +
                    '<div class="file-detail-item">' +
                        '<div class="file-detail-label">Size</div>' +
                        '<div class="file-detail-value">' + formatFileSize(info.file_size) + '</div>' +
                    '</div>';

                if (info.column_names && info.column_names.length > 0) {
                    if (columnList) columnList.style.display = 'block';
                    
                    if (columnItems) {
                        columnItems.innerHTML = info.column_names.map(function(name) {
                            const type = info.column_types[name];
                            return '<div class="column-item">' +
                                '<span class="column-name">' + name + '</span>' +
                                '<span class="column-type">' + type.type + '</span>' +
                            '</div>';
                        }).join('');
                    }
                }
            } else {
                fileDetailsGrid.innerHTML = 
                    '<div class="status-message status-message-error">' +
                        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
                            '<circle cx="12" cy="12" r="10"></circle>' +
                            '<line x1="15" y1="9" x2="9" y2="15"></line>' +
                            '<line x1="9" y1="9" x2="15" y2="15"></line>' +
                        '</svg>' +
                        '<span>Could not load file details</span>' +
                    '</div>';
            }
        })
        .catch(function(error) {
            if (loadingDetails) loadingDetails.style.display = 'none';
            console.error('Error fetching file details:', error);
        });
    }

    function performConversion(targetFormat) {
        const convertBtn = document.getElementById('convertBtn');
        
        setLoading(convertBtn, true);

        fetch('/convert', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: 'target_format=' + encodeURIComponent(targetFormat)
        })
        .then(response => response.json())
        .then(data => {
            setLoading(convertBtn, false);

            if (data.success) {
                showMessage(data.message, 'success');
                setTimeout(function() {
                    window.location.href = '/download';
                }, 800);
            } else {
                showMessage(data.message || 'Conversion failed', 'error');
            }
        })
        .catch(function(error) {
            setLoading(convertBtn, false);
            console.error('Conversion error:', error);
            showMessage('Conversion failed. Please try again.', 'error');
        });
    }

    function initDownload() {
        const downloadLink = document.getElementById('downloadLink');
        const downloadFilename = document.getElementById('downloadFilename');
    }

    document.addEventListener('DOMContentLoaded', function() {
        initThemeToggle();
        
        if (document.getElementById('uploadZone')) {
            initUpload();
        }
        
        if (document.getElementById('formatSelector')) {
            initConfigure();
        }
        
        if (document.getElementById('downloadLink')) {
            initDownload();
        }
    });

})();
