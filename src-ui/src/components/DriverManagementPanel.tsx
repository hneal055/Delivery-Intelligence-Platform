import React, { useEffect, useState } from 'react';

interface User {
    id: string;
    username: string;
    email: string;
    role: string;
    is_active: boolean;
}

const API_BASE_URL = "http://localhost:8000";

export const DriverManagementPanel: React.FC = () => {
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);
    const [message, setMessage] = useState<string | null>(null);

    const fetchUsers = async () => {
        try {
            setLoading(true);
            const token = localStorage.getItem("access_token") || "";
            const response = await fetch(${API_BASE_URL}/users, {
                headers: {
                    ...(token ? { Authorization: Bearer  } : {})
                }
            });
            if (!response.ok) {
                throw new Error(\Failed to fetch users: \\);
            }
            const data = await response.json();
            setUsers(data);
            setError(null);
        } catch (err: any) {
            console.error("Error fetching users:", err);
            setError(err.message || "Failed to load users");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchUsers();
    }, []);

    const toggleUserStatus = async (userId: string, isActive: boolean) => {
        try {
            const token = localStorage.getItem("access_token") || "";
            const endpoint = isActive ? \${API_BASE_URL}/users/\/disable\ : \${API_BASE_URL}/users/\/enable\;
            const response = await fetch(endpoint, {
                method: 'PUT',
                headers: {
                    ...(token ? { Authorization: Bearer  } : {})
                }
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Failed to update user status");
            }

            const result = await response.json();
            setMessage(result.message);
            fetchUsers();
        } catch (err: any) {
            setError(err.message);
        }
    };

    return (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 shadow-lg">
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h2 className="text-xl font-bold text-blue-400">Driver & User Management</h2>
                    <p className="text-gray-400 text-sm">Manage authentication credentials, roles, and account statuses.</p>
                </div>
                <button 
                    onClick={fetchUsers}
                    className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
                >
                    Refresh List
                </button>
            </div>

            {error && (
                <div className="mb-4 bg-red-950/50 border border-red-800 text-red-300 p-3 rounded-lg text-sm">
                    {error}
                </div>
            )}

            {message && (
                <div className="mb-4 bg-emerald-950/50 border border-emerald-800 text-emerald-300 p-3 rounded-lg text-sm">
                    {message}
                </div>
            )}

            {loading ? (
                <div className="text-center py-8 text-gray-400">Loading user profiles...</div>
            ) : (
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm text-gray-300">
                        <thead className="bg-gray-800 text-gray-400 uppercase text-xs">
                            <tr>
                                <th className="px-4 py-3">Username</th>
                                <th className="px-4 py-3">Email</th>
                                <th className="px-4 py-3">Role</th>
                                <th className="px-4 py-3">Status</th>
                                <th className="px-4 py-3 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-800">
                            {users.map((user) => (
                                <tr key={user.id} className="hover:bg-gray-800/50">
                                    <td className="px-4 py-3 font-medium text-white">{user.username}</td>
                                    <td className="px-4 py-3 text-gray-400">{user.email}</td>
                                    <td className="px-4 py-3">
                                        <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-950 text-blue-300 border border-blue-800">
                                            {user.role}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3">
                                        <span className={px-2.5 py-1 rounded-full text-xs font-semibold \}>
                                            {user.is_active ? 'Active' : 'Disabled'}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3 text-right">
                                        <button
                                            onClick={() => toggleUserStatus(user.id, user.is_active)}
                                            className={px-3 py-1.5 rounded-lg text-xs font-medium transition \}
                                        >
                                            {user.is_active ? 'Disable' : 'Enable'}
                                        </button>
                                    </td>
                                </tr>
                            ))}
                            {users.length === 0 && (
                                <tr>
                                    <td colSpan={5} className="text-center py-6 text-gray-500">No users found.</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
};

export default DriverManagementPanel;
