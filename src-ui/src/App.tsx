import React from 'react';
import FleetDashboard from './components/FleetDashboard';

function App() {
  return (
    <div className="min-h-screen bg-gray-950 text-white p-8">
      <header className="mb-8">
        <h1 className="text-3xl font-extrabold tracking-tight text-blue-400">
          DeskSOS Delivery Intelligence
        </h1>
        <p className="text-gray-400 text-sm mt-1">
          Real-time fleet tracking, heartbeats, and automated dispatch management.
        </p>
      </header>
      
      <main>
        <FleetDashboard />
      </main>
    </div>
  );
}

export default App;
