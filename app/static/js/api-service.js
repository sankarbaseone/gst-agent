/**
 * ApiService: Centralized backend communication layer.
 * No UI logic or data transformation allowed here.
 */
const ApiService = {
    /**
     * Upload invoices for reconciliation.
     * @param {File} file - CSV file
     * @param {string} tenantId - Tenant identifier
     * @param {string} plan - Subscription plan
     */
    async uploadInvoices(file, tenantId, plan) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/invoices/upload', {
            method: 'POST',
            headers: {
                'X-Tenant-ID': tenantId,
                'X-Plan': plan
            },
            body: formData
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Upload failed');
        }
        return data;
    },

    /**
     * Fetch the JSON risk report.
     * @param {string} tenantId 
     */
    async getRiskReportJSON(tenantId) {
        const response = await fetch('/reports/gst-risk', {
            method: 'GET',
            headers: {
                'X-Tenant-ID': tenantId
            }
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Failed to fetch report');
        }
        return data;
    },

    /**
     * Download the PDF risk report.
     * @param {string} tenantId 
     */
    async downloadRiskReportPDF(tenantId) {
        const response = await fetch('/reports/gst-risk/pdf', {
            method: 'GET',
            headers: {
                'X-Tenant-ID': tenantId
            }
        });

        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.detail || 'Failed to download PDF');
        }

        const blob = await response.blob();
        return {
            blob,
            filename: `GST_Risk_Report_${tenantId.slice(0, 8)}.pdf`
        };
    }
};
