'use strict';

// UI Elements
const currentEntity = document.getElementById('current-entity');
const entityProgress = document.getElementById('entity-progress');
const entityPercent = document.getElementById('entity-percent');
const syncLog = document.getElementById('sync-log');

function formatLastSync(lastSync) {
    if (!lastSync || lastSync === '2000-01-01T00:00:00Z') {
        return '-';
    }
    return new Date(lastSync).toLocaleString();
}

function formatEntityName(entity) {
    return entity
        .replace(/_/g, ' ')  // Replace underscores with spaces
        .replace(/-/g, ' ')  // Replace hyphens with spaces
        .split(' ')          // Split into words
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))  // Capitalize each word
        .join(' ');          // Join words back together
}

class XeroSyncProgress {
    constructor() {
        this.overallProgress = 0;
        this.currentEntityProgress = 0;
        this.currentEntity = null;
        this.totalEntities = window.XERO_ENTITIES.length;
        this.processedEntities = 0;
        this.eventSource = null;
        this.isInitialized = false;
        this.initializeSyncStatus();
        this.initializeSync();
    }

    async initializeSync() {
        // Check if a sync is already running
        const response = await fetch('/api/xero/sync-info/');
        const data = await response.json();
        
        if (data.sync_in_progress) {
            // If a sync is running, connect to its stream
            this.connectToStream();
        } else {
            // Start a new sync and wait for it to be ready
            const syncResponse = await fetch('/api/xero/sync/');
            if (!syncResponse.ok) {
                throw new Error('Failed to start sync');
            }
            // Wait a moment for the sync to be ready
            await new Promise(resolve => setTimeout(resolve, 1000));
            this.connectToStream();
        }
    }

    connectToStream() {
        this.eventSource = new EventSource('/api/xero/sync-stream/');
        
        this.eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleSyncEvent(data);
        };

        this.eventSource.onerror = (error) => {
            console.error('EventSource error:', error);
            this.eventSource.close();
            this.showError('Connection to sync stream lost');
        };
    }

    handleSyncEvent(data) {
        // Add message to log
        this.addLogMessage(data);

        // Update current entity if this is an entity-specific event
        if (data.entity && data.entity !== "sync") {
            this.currentEntity = data.entity;
        }

        // Update individual entity progress if we have a progress value
        if (data.progress !== null) {
            this.updateEntityProgress(data.entity, data.progress);
        }

        // If we see a completion message, mark that entity as done
        if (data.message.includes("No items to sync") || data.message.includes("Processed") || data.message.includes("Completed sync of")) {
            this.processedEntities++;
            this.overallProgress = (this.processedEntities / this.totalEntities) * 100;
            this.updateOverallProgress();
            this.updateEntityProgress(data.entity, 1.0);  // Set entity progress to 100%
            this.updateEntityRow(data.entity, {
                status: 'Completed',
                lastSync: new Date().toISOString()
            });
        }

        // If we see "Sync stream ended", close the connection gracefully
        if (data.message === "Sync stream ended") {
            this.eventSource.close();
        }
    }

    updateOverallProgress() {
        const overallBar = document.getElementById('overall-progress');
        const overallPercent = document.getElementById('overall-percent');
        const currentEntityLabel = document.getElementById('current-entity');

        if (overallBar && overallPercent) {
            overallBar.style.width = `${this.overallProgress}%`;
            overallPercent.textContent = `${Math.round(this.overallProgress)}%`;
        }

        if (currentEntityLabel) {
            currentEntityLabel.textContent = this.currentEntity ? 
                formatEntityName(this.currentEntity) : 
                'None';
        }
    }

    updateEntityProgress(entity, progress) {
        const entityBar = document.getElementById('entity-progress');
        const entityPercent = document.getElementById('entity-percent');

        if (entityBar && entityPercent) {
            entityBar.style.width = `${progress * 100}%`;
            entityPercent.textContent = `${Math.round(progress * 100)}%`;
        }
    }

    updateEntityRow(entity, updates = {}) {
        // Fail loudly if we get an unexpected entity
        if (!window.XERO_ENTITIES.includes(entity)) {
            console.error(`Unexpected entity type received: ${entity}`);
            throw new Error(`Unexpected entity type: ${entity}`);
        }
        
        const row = document.getElementById(`row-${entity}`);
        if (!row) {
            console.error(`Missing row for entity: ${entity}`);
            throw new Error(`Missing row for entity: ${entity}`);
        }

        // Update our stats object
        entityStats[entity] = { ...entityStats[entity], ...updates };
        const stats = entityStats[entity];

        // Update the row cells
        if (updates.lastSync) {
            const lastSyncDate = new Date(updates.lastSync);
            row.querySelector('.last-sync').textContent = formatLastSync(updates.lastSync);
        }
        if (updates.status) {
            const statusCell = row.querySelector('.status');
            statusCell.textContent = updates.status;
            
            // Update status classes
            statusCell.className = 'status'; // Reset classes
            switch (updates.status) {
                case 'In Progress':
                    statusCell.classList.add('status-in-progress');
                    break;
                case 'Completed':
                    statusCell.classList.add('status-completed');
                    break;
                case 'Error':
                    statusCell.classList.add('status-error');
                    break;
                default:
                    statusCell.classList.add('status-pending');
            }
        }
        if (updates.recordsUpdated !== undefined) {
            row.querySelector('.records').textContent = updates.recordsUpdated;
        }
    }

    addLogMessage(message) {
        const logContainer = document.getElementById('sync-log');
        if (!logContainer) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `log-entry ${message.severity || 'info'}`;
        
        // Format timestamp
        const timestamp = new Date(message.datetime).toLocaleTimeString();
        
        // Extract record count if present in message
        const recordMatch = message.message.match(/Updated (\d+) records?/i);
        if (recordMatch && message.entity) {
            this.updateEntityRow(message.entity, { recordsUpdated: parseInt(recordMatch[1], 10) });
        }
        
        messageDiv.textContent = `[${timestamp}] ${message.message}`;
        logContainer.appendChild(messageDiv);
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    showError(message) {
        const logContainer = document.getElementById('sync-log');
        if (!logContainer) return;

        const errorDiv = document.createElement('div');
        errorDiv.className = 'log-entry error';
        errorDiv.textContent = `ERROR ${message}`;
        logContainer.appendChild(errorDiv);
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    handleEntityChange(entity) {
        // Update current entity display
        if (currentEntity) {
            currentEntity.textContent = formatEntityName(entity);
        }
        
        // Reset entity progress
        this.currentEntityProgress = 0;
        this.updateEntityProgress(entity, 0);
        
        // Update status
        this.updateEntityRow(entity, {
            status: 'In Progress',
            lastSync: new Date().toISOString()
        });
    }

    handleEntityCompletion(entity, success = true, lastSync = null) {
        completedEntities++;
        this.updateEntityRow(entity, {
            status: success ? 'Completed' : 'Error',
            lastSync: lastSync || new Date().toISOString()
        });
    }

    syncComplete(success = true) {
        if (success) {
            // Could add success indicator here if needed
        }
    }

    disconnect() {
        if (this.eventSource) {
            this.eventSource.close();
        }
    }

    async initializeSyncStatus() {
        // Initialize the sync status table with current state
        window.XERO_ENTITIES.forEach(entity => {
            this.updateEntityRow(entity, {
                status: 'Pending',
                lastSync: '-',
                recordsUpdated: 0
            });
        });

        // Get last sync times from server
        try {
            const response = await fetch('/api/xero/sync-info/');
            const data = await response.json();
            
            // Update each entity with its last sync time
            Object.entries(data.last_syncs).forEach(([entity, lastSync]) => {
                if (lastSync) {
                    this.updateEntityRow(entity, {
                        lastSync: lastSync
                    });
                }
            });
        } catch (error) {
            console.error('Error fetching last sync times:', error);
        }
    }
}

// State tracking
let completedEntities = 0;
let entityStats = {};

// Initialize when the page loads
document.addEventListener('DOMContentLoaded', () => {
    // Initialize stats for each entity
    window.XERO_ENTITIES.forEach(entity => {
        entityStats[entity] = {
            status: 'Pending',
            lastSync: '-',
            recordsUpdated: 0
        };
    });

    window.xeroSyncProgress = new XeroSyncProgress();

    // Clean up when the page is unloaded
    window.addEventListener('unload', () => {
        if (window.xeroSyncProgress) {
            window.xeroSyncProgress.disconnect();
        }
    });
}); 