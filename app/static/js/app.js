function logout() {
    window.location.href = '/';
}

const fileInput = document.getElementById('file-input');
const uploadArea = document.getElementById('upload-area');
const processingState = document.getElementById('processing-state');
const resultsArea = document.getElementById('results-area');
const errorDiv = document.getElementById('upload-error');

fileInput.addEventListener('change', handleUpload);

async function handleUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    errorDiv.style.display = 'none';
    resultsArea.style.display = 'none';
    processingState.style.display = 'block';

    try {
        // Use ApiService for upload
        const data = await ApiService.uploadInvoices(file, CTX_TENANT_ID, CTX_PLAN);
        renderResults(data);
    } catch (err) {
        // Requirement 4: Propagation of errors
        errorDiv.textContent = 'Reconciliation could not be completed. ' + err.message;
        errorDiv.style.display = 'block';
    } finally {
        processingState.style.display = 'none';
        fileInput.value = '';
    }
}

function renderResults(data) {
    resultsArea.style.display = 'block';

    const results = data.reconciliation_results || [];

    // 1. Update Summary Cards
    const counts = { MATCHED: 0, PARTIAL_MATCH: 0, MISSING_IN_2B: 0, RISKY_ITC: 0 };
    results.forEach(r => {
        counts[r.status] = (counts[r.status] || 0) + 1;
    });

    document.getElementById('count-matched').textContent = counts.MATCHED;
    document.getElementById('count-partial').textContent = counts.PARTIAL_MATCH;
    document.getElementById('count-missing').textContent = counts.MISSING_IN_2B;
    document.getElementById('count-risky').textContent = counts.RISKY_ITC;

    // 2. Render Table (Max 1000 rows)
    const tbody = document.querySelector('#results-table tbody');
    tbody.innerHTML = '';

    results.slice(0, 1000).forEach(r => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${r.invoice_number}</td>
            <td>${r.gstin}</td>
            <td><span class="badge badge-${r.status}">${r.status.replace(/_/g, ' ')}</span></td>
            <td>${r.explanation}</td>
            <td>${r.suggested_action}</td>
        `;
        tbody.appendChild(tr);
    });

    // Update usage display
    document.getElementById('limit-usage').textContent = data.total_invoices;

    // Render Vendor Summary
    const vendorSummary = data.vendor_summary || [];
    if (vendorSummary.length > 0) {
        const vendorSection = document.getElementById('vendor-risk-section');
        vendorSection.style.display = 'block';

        const vendorTbody = document.querySelector('#vendor-table tbody');
        vendorTbody.innerHTML = '';

        vendorSummary.forEach(v => {
            const tr = document.createElement('tr');
            const riskClass = v.vendor_risk_level === 'HIGH' ? 'RISKY_ITC' : (v.vendor_risk_level === 'MEDIUM' ? 'PARTIAL_MATCH' : 'MATCHED');
            tr.innerHTML = `
                <td>${v.vendor_gstin}</td>
                <td>${v.total_invoices}</td>
                <td>${v.missing_in_2b_count}</td>
                <td>${v.risky_count}</td>
                <td><span class="badge badge-${riskClass}">${v.vendor_risk_level}</span></td>
            `;
            vendorTbody.appendChild(tr);
        });
    }
}

async function downloadPDF() {
    try {
        // Use ApiService for PDF download
        const { blob, filename } = await ApiService.downloadRiskReportPDF(CTX_TENANT_ID);

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
    } catch (err) {
        alert(err.message);
    }
}
