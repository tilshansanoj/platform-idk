import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

function App() {
  const [deployments, setDeployments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    instanceName: '',
    instanceType: 't2.micro',
    amiId: 'ami-0c55b159cbfafe1f0',
    keyName: ''
  });

  useEffect(() => {
    loadDeployments();
  }, []);

  const loadDeployments = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/deployments`);
      setDeployments(response.data.deployments);
    } catch (error) {
      toast.error('Failed to load deployments');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const response = await axios.post(`${API_BASE_URL}/deploy`, formData);
      toast.success(response.data.message);
      setFormData({ ...formData, instanceName: '', keyName: '' });
      loadDeployments();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Deployment failed');
    } finally {
      setLoading(false);
    }
  };

  const syncDeployment = async (deploymentId) => {
    try {
      await axios.post(`${API_BASE_URL}/deployments/${deploymentId}/sync`);
      toast.success('Deployment synced');
      loadDeployments();
    } catch (error) {
      toast.error('Sync failed');
    }
  };

  const terminateDeployment = async (deploymentId, instanceId) => {
    if (!window.confirm(`Are you sure you want to terminate instance ${instanceId}?`)) return;
    
    try {
      await axios.delete(`${API_BASE_URL}/deployments/${deploymentId}`);
      toast.success('Termination initiated');
      loadDeployments();
    } catch (error) {
      toast.error('Termination failed');
    }
  };

  return (
    <div className="App">
      <div className="container">
        <h1>AWS EC2 Instance Deployer</h1>
        
        <div className="form-container">
          <h2>Deploy New Instance</h2>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Instance Name:</label>
              <input
                type="text"
                value={formData.instanceName}
                onChange={(e) => setFormData({ ...formData, instanceName: e.target.value })}
                placeholder="MyWebServer"
                required
              />
            </div>
            
            <div className="form-group">
              <label>Instance Type:</label>
              <select
                value={formData.instanceType}
                onChange={(e) => setFormData({ ...formData, instanceType: e.target.value })}
                required
              >
                <option value="t2.micro">t2.micro (Free Tier)</option>
                <option value="t2.small">t2.small</option>
                <option value="t2.medium">t2.medium</option>
                <option value="t3.micro">t3.micro</option>
                <option value="t3.small">t3.small</option>
              </select>
            </div>
            
            <div className="form-group">
              <label>AMI ID:</label>
              <input
                type="text"
                value={formData.amiId}
                onChange={(e) => setFormData({ ...formData, amiId: e.target.value })}
                placeholder="ami-0c55b159cbfafe1f0"
                required
              />
              <small>Amazon Linux 2 AMI (us-east-1)</small>
            </div>
            
            <div className="form-group">
              <label>Key Pair Name:</label>
              <input
                type="text"
                value={formData.keyName}
                onChange={(e) => setFormData({ ...formData, keyName: e.target.value })}
                placeholder="my-key-pair"
                required
              />
              <small>Must exist in your AWS account</small>
            </div>
            
            <button type="submit" disabled={loading}>
              {loading ? 'Deploying...' : 'Deploy Instance'}
            </button>
          </form>
        </div>

        <div className="deployments-container">
          <h2>Deployment History</h2>
          <div className="controls">
            <button onClick={loadDeployments}>Refresh</button>
            <button onClick={() => deployments.forEach(d => syncDeployment(d.id))}>
              Sync All
            </button>
          </div>
          
          <div className="deployments-list">
            {deployments.map(deployment => (
              <div key={deployment.id} className="deployment-card">
                <div className="deployment-header">
                  <h3>{deployment.instance_name}</h3>
                  <span className={`status status-${deployment.status}`}>
                    {deployment.status}
                  </span>
                </div>
                
                <div className="deployment-details">
                  <p><strong>Instance ID:</strong> {deployment.instance_id}</p>
                  <p><strong>Type:</strong> {deployment.instance_type}</p>
                  <p><strong>AMI:</strong> {deployment.ami_id}</p>
                  {deployment.public_ip && <p><strong>Public IP:</strong> {deployment.public_ip}</p>}
                  {deployment.private_ip && <p><strong>Private IP:</strong> {deployment.private_ip}</p>}
                  <p><strong>Launched:</strong> {new Date(deployment.launch_time).toLocaleString()}</p>
                </div>
                
                <div className="deployment-actions">
                  <button onClick={() => syncDeployment(deployment.id)}>Sync</button>
                  <button 
                    onClick={() => terminateDeployment(deployment.id, deployment.instance_id)}
                    disabled={deployment.status === 'terminating' || deployment.status === 'terminated'}
                  >
                    Terminate
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
      
      <ToastContainer position="top-right" autoClose={3000} />
    </div>
  );
}

export default App;