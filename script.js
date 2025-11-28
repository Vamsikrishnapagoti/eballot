// script.js - EBallot JavaScript

// Configuration
const API_BASE_URL = "http://localhost:5000/api";


// State
let currentUser = null;
let authToken = null;
let elections = [];
let candidates = [];

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    authToken = localStorage.getItem('authToken');
    const savedUser = localStorage.getItem('currentUser');
    
    if (authToken && savedUser) {
        currentUser = JSON.parse(savedUser);
        showNavigation();
        showSection('dashboard');
        loadDashboardData();
    } else {
        showSection('home');
    }
});

// Section Navigation
function showSection(sectionId) {
    const sections = document.querySelectorAll('.section');
    sections.forEach(section => {
        section.classList.remove('active');
    });
    
    const targetSection = document.getElementById(sectionId);
    if (targetSection) {
        targetSection.classList.add('active');
    }
    
    if (sectionId === 'voting') {
        loadElectionsForVoting();
    } else if (sectionId === 'results') {
        loadElectionsForResults();
    }
}

// Show/Hide Navigation
function showNavigation() {
    document.getElementById('mainNav').style.display = 'flex';
}

function hideNavigation() {
    document.getElementById('mainNav').style.display = 'none';
}

// Registration
async function handleRegister(event) {
    event.preventDefault();
    
    const data = {
        voterId: document.getElementById('regVoterId').value.trim(),
        firstName: document.getElementById('regFirstName').value.trim(),
        middleName: document.getElementById('regMiddleName').value.trim(),
        lastName: document.getElementById('regLastName').value.trim(),
        mobile: document.getElementById('regMobile').value.trim(),
        aadhar: document.getElementById('regAadhar').value.trim(),
        email: document.getElementById('regEmail').value.trim(),
        dob: document.getElementById('regDob').value,
        address: document.getElementById('regAddress').value.trim(),
        password: document.getElementById('regPassword').value,
        declaration: document.getElementById('regDeclaration').checked
    };
    
    // Validate mobile (10 digits)
    if (data.mobile.length !== 10 || !/^\d{10}$/.test(data.mobile)) {
        showAlert('registerAlert', 'Mobile number must be exactly 10 digits', 'danger');
        return;
    }
    
    // Validate Aadhar (12 digits)
    if (data.aadhar.length !== 12 || !/^\d{12}$/.test(data.aadhar)) {
        showAlert('registerAlert', 'Aadhar number must be exactly 12 digits', 'danger');
        return;
    }
    
    // Validate age (18+)
    const dob = new Date(data.dob);
    const age = Math.floor((new Date() - dob) / (365.25 * 24 * 60 * 60 * 1000));
    if (age < 18) {
        showAlert('registerAlert', 'You must be at least 18 years old to register', 'danger');
        return;
    }
    
    // Validate declaration
    if (!data.declaration) {
        showAlert('registerAlert', 'You must accept the declaration', 'danger');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert('registerAlert', 'Registration successful! Redirecting to login...', 'success');
            document.getElementById('registerForm').reset();
            setTimeout(() => showSection('login'), 2000);
        } else {
            showAlert('registerAlert', result.error || 'Registration failed', 'danger');
        }
    } catch (error) {
        console.error('Registration error:', error);
        showAlert('registerAlert', 'Network error. Please check if backend server is running.', 'danger');
    }
}

// Login
async function handleLogin(event) {
    event.preventDefault();
    
    const data = {
        voterId: document.getElementById('loginVoterId').value.trim(),
        password: document.getElementById('loginPassword').value
    };
    
    try {
        const response = await fetch(`${API_BASE_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            authToken = result.token;
            currentUser = result.voter;
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            
            showAlert('loginAlert', 'Login successful! Redirecting...', 'success');
            document.getElementById('loginForm').reset();
            
            setTimeout(() => {
                showNavigation();
                showSection('dashboard');
                loadDashboardData();
            }, 1000);
        } else {
            showAlert('loginAlert', result.error || 'Login failed', 'danger');
        }
    } catch (error) {
        console.error('Login error:', error);
        showAlert('loginAlert', 'Network error. Please check if backend server is running.', 'danger');
    }
}

// Logout
function logout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
    hideNavigation();
    showSection('home');
}

// Load Dashboard Data
async function loadDashboardData() {
    if (!currentUser) return;
    
    document.getElementById('voterName').textContent = currentUser.name;
    document.getElementById('voterIdDisplay').textContent = currentUser.voterId;
    
    try {
        const response = await fetch(`${API_BASE_URL}/dashboard/stats`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            const stats = await response.json();
            document.getElementById('activeElections').textContent = stats.active_elections;
            document.getElementById('upcomingElections').textContent = stats.upcoming_elections;
            document.getElementById('completedElections').textContent = stats.completed_elections;
            document.getElementById('votesCast').textContent = stats.votes_cast;
        }
    } catch (error) {
        console.error('Dashboard load error:', error);
    }
}

// Load Elections for Voting
async function loadElectionsForVoting() {
    try {
        const response = await fetch(`${API_BASE_URL}/elections?status=active`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            elections = data.elections;
            
            const select = document.getElementById('electionSelect');
            select.innerHTML = '<option value="">Choose an election...</option>';
            
            elections.forEach(election => {
                const option = document.createElement('option');
                option.value = election.election_id;
                option.textContent = election.election_name;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Elections load error:', error);
        showAlert('votingAlert', 'Failed to load elections. Please check backend connection.', 'danger');
    }
}

// Load Candidates
async function loadCandidates() {
    const electionId = document.getElementById('electionSelect').value;
    
    if (!electionId) {
        document.getElementById('candidatesList').innerHTML = '';
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/elections/${electionId}/candidates`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            candidates = data.candidates;
            displayCandidates();
        }
    } catch (error) {
        console.error('Candidates load error:', error);
        showAlert('votingAlert', 'Failed to load candidates', 'danger');
    }
}

// Display Candidates
function displayCandidates() {
    const container = document.getElementById('candidatesList');
    
    if (candidates.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #64748b;">No candidates available for this election.</p>';
        return;
    }
    
    container.innerHTML = candidates.map(candidate => `
        <div class="candidate-card">
            <h3>${candidate.candidate_name}</h3>
            <p class="candidate-party">${candidate.party_name || 'Independent'}</p>
            <p class="candidate-desc">${candidate.description || 'No description available'}</p>
            <button class="btn btn--primary btn--full-width" onclick="castVote('${candidate.candidate_id}')">
                Vote for ${candidate.candidate_name}
            </button>
        </div>
    `).join('');
}

// Cast Vote
async function castVote(candidateId) {
    const electionId = document.getElementById('electionSelect').value;
    
    if (!confirm('Are you sure you want to cast your vote? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/vote`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                electionId: electionId,
                candidateId: parseInt(candidateId)
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert('votingAlert', 'Vote cast successfully! Thank you for voting.', 'success');
            document.getElementById('candidatesList').innerHTML = '';
            document.getElementById('electionSelect').value = '';
            loadDashboardData();
        } else {
            showAlert('votingAlert', result.error || 'Failed to cast vote', 'danger');
        }
    } catch (error) {
        console.error('Vote cast error:', error);
        showAlert('votingAlert', 'Network error. Please try again.', 'danger');
    }
}

// Load Elections for Results
async function loadElectionsForResults() {
    try {
        const response = await fetch(`${API_BASE_URL}/elections?status=active`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            
            const select = document.getElementById('resultsElectionSelect');
            select.innerHTML = '<option value="">Choose an election...</option>';
            
            data.elections.forEach(election => {
                const option = document.createElement('option');
                option.value = election.election_id;
                option.textContent = election.election_name;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Elections load error:', error);
    }
}

// Load Results
async function loadResults() {
    const electionId = document.getElementById('resultsElectionSelect').value;
    
    if (!electionId) {
        document.getElementById('resultsContainer').innerHTML = '';
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/elections/${electionId}/results`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            displayResults(data);
        }
    } catch (error) {
        console.error('Results load error:', error);
        document.getElementById('resultsContainer').innerHTML = 
            '<p style="text-align: center; color: #ef4444;">Failed to load results. Please try again.</p>';
    }
}

// Display Results
function displayResults(data) {
    const container = document.getElementById('resultsContainer');
    
    if (data.results.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #64748b;">No results available yet.</p>';
        return;
    }
    
    let html = `
        <div class="results-header">
            <h3>Total Votes Cast: ${data.total_votes}</h3>
        </div>
        <div class="results-list">
    `;
    
    data.results.forEach(result => {
        html += `
            <div class="result-item">
                <div class="result-header">
                    <span class="result-candidate">${result.candidate_name}</span>
                    <span class="result-votes">${result.vote_count} votes</span>
                </div>
                <p class="result-party">${result.party_name || 'Independent'}</p>
                <div class="result-bar">
                    <div class="result-bar-fill" style="width: ${result.percentage || 0}%">
                        ${result.percentage || 0}%
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

// Show Alert
function showAlert(elementId, message, type) {
    const alertDiv = document.getElementById(elementId);
    alertDiv.innerHTML = `
        <div class="alert alert-${type}">
            ${message}
        </div>
    `;
    
    setTimeout(() => {
        alertDiv.innerHTML = '';
    }, 5000);
}
