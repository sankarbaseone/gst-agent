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

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/invoices/upload', {
            method: 'POST',
            headers: {
                'X-Tenant-ID': CTX_TENANT_ID,
                'X-Plan': CTX_PLAN
            },
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            // Requirement 4: User-safe reconciliation failure message
            throw new Error('Reconciliation could not be completed. ' + (data.detail || 'Please try again.'));
        }

        renderResults(data);

    } catch (err) {
        errorDiv.textContent = err.message;
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
        const response = await fetch('/reports/gst-risk', {
            method: 'GET',
            headers: {
                'X-Tenant-ID': CTX_TENANT_ID
            }
        });

        if (!response.ok) throw new Error('Failed to generate report.');

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `GST_Risk_Report_${CTX_TENANT_ID.slice(0, 8)}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
    } catch (err) {
        alert(err.message);
    }
}
