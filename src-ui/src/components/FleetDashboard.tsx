import React, { useEffect, useState } from 'react';

interface Driver {
    driver_id: string;
    is_online: boolean;
    latitude: number;
    longitude: number;
}

interface AssignmentResult {
    order_id: string;
    assigned_driver_id: string;
    message: string;
}

const API_BASE_URL = "http://localhost:8000";

export const FleetDashboard: React.FC = () => {
    const [drivers, setDrivers] = useState<Driver[]>([]);
    const [onlineCount, setOnlineCount] = useState<number>(0);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);
    const [assigning, setAssigning] = useState<boolean>(false);
    const [lastAssignment, setLastAssignment] = useState<AssignmentResult | null>(null);

    const fetchFleetData = async () => {
        try {
            const response = await fetch(\\/dispatch/drivers\);
            if (!response.ok) {
                throw new Error(\Server returned status \\);
            }
            const data = await response.json();
            setDrivers(data.drivers || []);
            setOnlineCount(data.online_count || 0);
            setError(null);
        } catch (err: any) {
            console.error("Failed to fetch live fleet data from backend:", err);
            setError(err.message || "Connection failed");
            setDrivers([
                { driver_id: "D001", is_online: true, latitude: 41.8781, longitude: -87.6298 },
                { driver_id: "D002", is_online: false, latitude: 41.8850, longitude: -87.6350 }
            ]);
            setOnlineCount(1);
        } finally {
            setLoading(false);
        }
    };

    const handleSimulateOrder = async () => {
        setAssigning(true);
        setLastAssignment(null);
        try {
            const orderPayload = {
                order_id: \ORD-\\,
                destination_latitude: 41.8781 + (Math.random() * 0.02 - 0.01),
                destination_longitude: -87.6298 + (Math.random() * 0.02 - 0.01)
            };

            const response = await fetch(\\/dispatch/assign\, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(orderPayload)
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Assignment failed');
            }

            const result = await response.json();
            setLastAssignment(result);
        } catch (err: any) {
            alert(\Assignment error: \\);
        } finally {
            setAssigning(false);
        }
    };

    useEffect(() => {
        fetchFleetData();
        const interval = setInterval(fetchFleetData, 5000);
        return () => clearInterval(interval);
    }, []);

    if (loading) {
        return <div className="p-6 text-white text-center">Connecting to Delivery Intelligence Backend...</div>;
    }

    return (
        <div className="space-y-6">
            {error && (
                <div className="bg-amber-950 border border-amber-800 text-amber-300 px-4 py-3 rounded-lg text-sm">
                    <span className="font-semibold">Backend Notice:</span> Running in fallback mode ({error}). Ensure FastAPI is running on port 8000.
                </div>
            )}

            <div className="grid grid-cols-3 gap-4">
                <div className="bg-gray-900 p-6 rounded-lg border border-gray-800 shadow-md">
                    <p className="text-gray-400 text-sm font-medium">Active Online Drivers</p>
                    <p className="text-4xl font-extrabold text-green-400 mt-2">{onlineCount} / {drivers.length}</p>
                </div>
                <div className="bg-gray-900 p-6 rounded-lg border border-gray-800 shadow-md">
                    <p className="text-gray-400 text-sm font-medium">System Dispatch Status</p>
                    <p className="text-xl font-semibold text-blue-400 mt-2">Operational (Live Polling)</p>
                </div>
                <div className="bg-gray-900 p-6 rounded-lg border border-gray-800 shadow-md flex flex-col justify-between">
                    <p className="text-gray-400 text-sm font-medium">Automated Dispatch Action</p>
                    <button
                        onClick={handleSimulateOrder}
                        disabled={assigning}
                        className="mt-2 w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold py-2 px-4 rounded transition disabled:opacity-50"
                    >
                        {assigning ? 'Assigning Optimal Driver...' : 'Simulate New Order'}
                    </button>
                </div>
            </div>

            {lastAssignment && (
                <div className="bg-green-950/80 border border-green-800 text-green-200 p-4 rounded-lg shadow flex justify-between items-center">
                    <div>
                        <span className="font-bold">Match Successful!</span> {lastAssignment.message}
                    </div>
                    <span className="text-xs bg-green-900 border border-green-700 px-2.5 py-1 rounded font-mono">
                        Assigned Driver: {lastAssignment.assigned_driver_id}
                    </span>
                </div>
            )}

            <div className="bg-gray-900 rounded-lg border border-gray-800 shadow-md overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-800 flex justify-between items-center">
                    <h3 className="text-lg font-bold">Driver Fleet Grid</h3>
                    <button 
                        onClick={fetchFleetData}
                        className="text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 px-3 py-1.5 rounded border border-gray-700 transition"
                    >
                        Refresh Now
                    </button>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-sm">
                        <thead>
                            <tr className="bg-gray-950 text-gray-400 border-b border-gray-800">
                                <th className="py-3 px-6">Driver ID</th>
                                <th className="py-3 px-6">Status</th>
                                <th className="py-3 px-6">Latitude</th>
                                <th className="py-3 px-6">Longitude</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-800">
                            {drivers.map((driver) => (
                                <tr key={driver.driver_id} className="hover:bg-gray-850/50">
                                    <td className="py-3 px-6 font-semibold text-gray-200">{driver.driver_id}</td>
                                    <td className="py-3 px-6">
                                        <span className={px-2.5 py-1 rounded-full text-xs font-semibold }>
                                            {driver.is_online ? 'ONLINE' : 'OFFLINE'}
                                        </span>
                                    </td>
                                    <td className="py-3 px-6 text-gray-300">{driver.latitude?.toFixed(4) ?? 'N/A'}</td>
                                    <td className="py-3 px-6 text-gray-300">{driver.longitude?.toFixed(4) ?? 'N/A'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};
export default FleetDashboard;
