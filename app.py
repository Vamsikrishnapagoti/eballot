# app.py - EBallot Backend Server


from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import jwt
import os
from functools import wraps
app = Flask(__name__)
CORS(app)
# Configuration
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['JWT_EXPIRATION_HOURS'] = 24

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Vapo@0209',  # PUT YOUR MYSQL PASSWORD HERE
    'database': 'eballot_db',
    'port': 3306
}

# Database Connection
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return None

# JWT Token Required Decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_voter_id = data['voter_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(current_voter_id, *args, **kwargs)
    
    return decorated

# Log Audit
def log_audit(voter_id, action, details, ip_address):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO audit_logs (voter_id, action, details, ip_address) VALUES (%s, %s, %s, %s)",
                (voter_id, action, details, ip_address)
            )
            conn.commit()
        except mysql.connector.Error as err:
            print(f"Audit log error: {err}")
        finally:
            cursor.close()
            conn.close()

# ========== API ROUTES ==========

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'message': 'EBallot API is running'}), 200

# ========== VOTER REGISTRATION ==========

@app.route('/api/register', methods=['POST'])
def register_voter():
    data = request.json
    ip_address = request.remote_addr
    
    required_fields = ['voterId', 'firstName', 'lastName', 'mobile', 'aadhar', 
                      'email', 'dob', 'address', 'password', 'declaration']
    
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    if len(data['mobile']) != 10 or not data['mobile'].isdigit():
        return jsonify({'error': 'Mobile number must be exactly 10 digits'}), 400
    
    if len(data['aadhar']) != 12 or not data['aadhar'].isdigit():
        return jsonify({'error': 'Aadhar number must be exactly 12 digits'}), 400
    
    try:
        dob = datetime.strptime(data['dob'], '%Y-%m-%d')
        age = (datetime.now() - dob).days // 365
        if age < 18:
            return jsonify({'error': 'You must be at least 18 years old to register'}), 400
    except ValueError:
        return jsonify({'error': 'Invalid date of birth format'}), 400
    
    if not data['declaration']:
        return jsonify({'error': 'You must accept the declaration'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT voter_id FROM voters WHERE email = %s OR mobile = %s OR aadhar = %s OR voter_id = %s",
            (data['email'], data['mobile'], data['aadhar'], data['voterId'])
        )
        
        if cursor.fetchone():
            return jsonify({'error': 'A voter with this email, mobile, Aadhar, or ID already exists'}), 409
        
        password_hash = generate_password_hash(data['password'])
        
        cursor.execute(
            """INSERT INTO voters 
            (voter_id, first_name, middle_name, last_name, mobile, aadhar, email, 
            date_of_birth, residential_address, password_hash) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (data['voterId'], data['firstName'], data.get('middleName', ''), 
             data['lastName'], data['mobile'], data['aadhar'], data['email'], 
             data['dob'], data['address'], password_hash)
        )
        
        conn.commit()
        log_audit(data['voterId'], 'REGISTRATION', 'New voter registered', ip_address)
        
        return jsonify({
            'message': 'Registration successful',
            'voterId': data['voterId']
        }), 201
        
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'error': f'Registration failed: {str(err)}'}), 500
    
    finally:
        cursor.close()
        conn.close()

# ========== VOTER LOGIN ==========

@app.route('/api/login', methods=['POST'])
def login_voter():
    data = request.json
    ip_address = request.remote_addr
    
    if not data.get('voterId') or not data.get('password'):
        return jsonify({'error': 'Voter ID and password are required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute(
            """SELECT voter_id, first_name, middle_name, last_name, email, 
            password_hash, is_active FROM voters WHERE voter_id = %s""",
            (data['voterId'],)
        )
        
        voter = cursor.fetchone()
        
        if not voter or not check_password_hash(voter['password_hash'], data['password']):
            log_audit(data['voterId'], 'LOGIN_FAILED', 'Invalid credentials', ip_address)
            return jsonify({'error': 'Invalid Voter ID or password'}), 401
        
        if not voter['is_active']:
            return jsonify({'error': 'Your account has been deactivated'}), 403
        
        token = jwt.encode({
            'voter_id': voter['voter_id'],
            'exp': datetime.utcnow() + timedelta(hours=app.config['JWT_EXPIRATION_HOURS'])
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        full_name = f"{voter['first_name']} {voter['middle_name']} {voter['last_name']}" if voter['middle_name'] else f"{voter['first_name']} {voter['last_name']}"
        
        log_audit(voter['voter_id'], 'LOGIN_SUCCESS', 'User logged in', ip_address)
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'voter': {
                'voterId': voter['voter_id'],
                'name': full_name,
                'email': voter['email']
            }
        }), 200
        
    except mysql.connector.Error as err:
        return jsonify({'error': f'Login failed: {str(err)}'}), 500
    
    finally:
        cursor.close()
        conn.close()

# ========== GET ELECTIONS ==========

@app.route('/api/elections', methods=['GET'])
@token_required
def get_elections(current_voter_id):
    status = request.args.get('status', 'active')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute(
            """SELECT election_id, election_name, description, start_date, 
            end_date, status FROM elections WHERE status = %s 
            ORDER BY start_date DESC""",
            (status,)
        )
        
        elections = cursor.fetchall()
        
        for election in elections:
            election['start_date'] = election['start_date'].strftime('%Y-%m-%d %H:%M:%S')
            election['end_date'] = election['end_date'].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify({'elections': elections}), 200
        
    except mysql.connector.Error as err:
        return jsonify({'error': f'Failed to fetch elections: {str(err)}'}), 500
    
    finally:
        cursor.close()
        conn.close()

# ========== GET CANDIDATES ==========

@app.route('/api/elections/<election_id>/candidates', methods=['GET'])
@token_required
def get_candidates(current_voter_id, election_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute(
            """SELECT candidate_id, candidate_name, party_name, description, photo_url 
            FROM candidates WHERE election_id = %s ORDER BY candidate_id""",
            (election_id,)
        )
        
        candidates = cursor.fetchall()
        
        return jsonify({'candidates': candidates}), 200
        
    except mysql.connector.Error as err:
        return jsonify({'error': f'Failed to fetch candidates: {str(err)}'}), 500
    
    finally:
        cursor.close()
        conn.close()

# ========== CAST VOTE ==========

@app.route('/api/vote', methods=['POST'])
@token_required
def cast_vote(current_voter_id):
    data = request.json
    ip_address = request.remote_addr
    
    if not data.get('electionId') or not data.get('candidateId'):
        return jsonify({'error': 'Election ID and Candidate ID are required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute(
            "SELECT status FROM elections WHERE election_id = %s",
            (data['electionId'],)
        )
        election = cursor.fetchone()
        
        if not election:
            return jsonify({'error': 'Election not found'}), 404
        
        if election['status'] != 'active':
            return jsonify({'error': 'This election is not currently active'}), 400
        
        cursor.execute(
            "SELECT vote_id FROM votes WHERE voter_id = %s AND election_id = %s",
            (current_voter_id, data['electionId'])
        )
        
        if cursor.fetchone():
            return jsonify({'error': 'You have already voted in this election'}), 409
        
        cursor.execute(
            """INSERT INTO votes (voter_id, election_id, candidate_id, ip_address) 
            VALUES (%s, %s, %s, %s)""",
            (current_voter_id, data['electionId'], data['candidateId'], ip_address)
        )
        
        conn.commit()
        
        log_audit(current_voter_id, 'VOTE_CAST', 
                 f"Vote cast for election: {data['electionId']}", ip_address)
        
        return jsonify({'message': 'Vote cast successfully'}), 201
        
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'error': f'Failed to cast vote: {str(err)}'}), 500
    
    finally:
        cursor.close()
        conn.close()

# ========== GET RESULTS ==========

@app.route('/api/elections/<election_id>/results', methods=['GET'])
@token_required
def get_results(current_voter_id, election_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute(
            "SELECT COUNT(*) as total_votes FROM votes WHERE election_id = %s",
            (election_id,)
        )
        total_votes = cursor.fetchone()['total_votes']
        
        cursor.execute(
            """SELECT c.candidate_id, c.candidate_name, c.party_name, 
            COUNT(v.vote_id) as vote_count,
            ROUND(COUNT(v.vote_id) * 100.0 / %s, 2) as percentage
            FROM candidates c
            LEFT JOIN votes v ON c.candidate_id = v.candidate_id AND v.election_id = %s
            WHERE c.election_id = %s
            GROUP BY c.candidate_id, c.candidate_name, c.party_name
            ORDER BY vote_count DESC""",
            (total_votes if total_votes > 0 else 1, election_id, election_id)
        )
        
        results = cursor.fetchall()
        
        return jsonify({
            'election_id': election_id,
            'total_votes': total_votes,
            'results': results
        }), 200
        
    except mysql.connector.Error as err:
        return jsonify({'error': f'Failed to fetch results: {str(err)}'}), 500
    
    finally:
        cursor.close()
        conn.close()

# ========== DASHBOARD STATS ==========

@app.route('/api/dashboard/stats', methods=['GET'])
@token_required
def get_dashboard_stats(current_voter_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT COUNT(*) as count FROM elections WHERE status = 'active'")
        active_elections = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM elections WHERE status = 'upcoming'")
        upcoming_elections = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM elections WHERE status = 'completed'")
        completed_elections = cursor.fetchone()['count']
        
        cursor.execute(
            "SELECT COUNT(*) as count FROM votes WHERE voter_id = %s",
            (current_voter_id,)
        )
        votes_cast = cursor.fetchone()['count']
        
        return jsonify({
            'active_elections': active_elections,
            'upcoming_elections': upcoming_elections,
            'completed_elections': completed_elections,
            'votes_cast': votes_cast
        }), 200
        
    except mysql.connector.Error as err:
        return jsonify({'error': f'Failed to fetch stats: {str(err)}'}), 500
    
    finally:
        cursor.close()
        conn.close()

# ========== RUN APP ==========

if __name__ == '__main__':
    print("=" * 60)
    print("EBallot Backend Server Starting...")
    print("=" * 60)
    print(f"Server will run on: http://localhost:5000")
    print(f"API Base URL: http://localhost:5000/api")
    print("=" * 60)
    print("Make sure MySQL is running and database is set up!")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
