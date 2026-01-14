import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Mail, Lock, ArrowLeft, CheckCircle, XCircle } from 'lucide-react'
import { supabase } from '../lib/supabase'

function Login() {
    const navigate = useNavigate()
    const [isLogin, setIsLogin] = useState(true)
    const [formData, setFormData] = useState({
        email: '',
        name: '',
        password: '',
        confirmPassword: ''
    })
    const [loading, setLoading] = useState(false)
    const [message, setMessage] = useState({ type: '', text: '' })

    const handleSubmit = async (e) => {
        e.preventDefault()
        setLoading(true)
        setMessage({ type: '', text: '' })

        try {
            if (isLogin) {
                // Login logic
                const { data, error } = await supabase
                    .from('users_voice')
                    .select('*')
                    .eq('email_address', formData.email)
                    .eq('password', formData.password)
                    .single()

                if (error || !data) {
                    setMessage({ type: 'error', text: 'Invalid email or password' })
                } else {
                    setMessage({ type: 'success', text: 'Login successful! Welcome back.' })
                    // Store user info in localStorage
                    localStorage.setItem('user', JSON.stringify({ email: data.email_address, name: data.name }))
                    setTimeout(() => navigate('/'), 1500)
                }
            } else {
                // Register logic
                if (formData.password !== formData.confirmPassword) {
                    setMessage({ type: 'error', text: 'Passwords do not match' })
                    setLoading(false)
                    return
                }

                // Check if user already exists
                const { data: existingUser } = await supabase
                    .from('users_voice')
                    .select('email_address')
                    .eq('email_address', formData.email)
                    .single()

                if (existingUser) {
                    setMessage({ type: 'error', text: 'Email already registered' })
                } else {
                    // Insert new user
                    const { error } = await supabase
                        .from('users_voice')
                        .insert([
                            {
                                email_address: formData.email,
                                name: formData.name,
                                password: formData.password
                            }
                        ])

                    if (error) {
                        setMessage({ type: 'error', text: 'Registration failed. Please try again.' })
                    } else {
                        setMessage({ type: 'success', text: 'Registration successful! You can now login.' })
                        setTimeout(() => setIsLogin(true), 1500)
                    }
                }
            }
        } catch (error) {
            setMessage({ type: 'error', text: 'An error occurred. Please try again.' })
        } finally {
            setLoading(false)
        }
    }

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        })
    }

    return (
        <div className="min-h-screen bg-black text-white">
            {/* Navigation */}
            <nav className="flex items-center justify-between px-8 py-5 border-b border-gray-800">
                <div className="text-2xl font-bold">NextGen Voice</div>
                <button
                    onClick={() => navigate('/')}
                    className="flex items-center gap-2 px-4 py-2 text-sm hover:text-gray-300 transition"
                >
                    <ArrowLeft className="w-4 h-4" />
                    Back to Home
                </button>
            </nav>

            {/* Login Form */}
            <main className="relative overflow-hidden min-h-screen flex items-center justify-center">
                {/* Background effects */}
                <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1000px] h-[1000px] bg-gradient-radial from-green-500/20 via-green-500/5 to-transparent blur-3xl -z-10"></div>
                <div className="absolute top-2/3 left-1/4 w-[600px] h-[600px] bg-gradient-radial from-emerald-500/15 to-transparent blur-3xl -z-10"></div>
                <div className="absolute top-1/2 right-1/4 w-[500px] h-[500px] bg-gradient-radial from-teal-500/10 to-transparent blur-3xl -z-10"></div>
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.05)_1px,transparent_1px)] bg-[length:20px_20px] -z-10"></div>
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(16,185,129,0.03)_1px,transparent_1px)] bg-[length:40px_40px] -z-10"></div>
                <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[length:100px_100px] -z-10"></div>

                <div className="w-full max-w-md px-8 relative z-10">
                    <div className="bg-gray-900/50 backdrop-blur-sm border border-gray-800 rounded-2xl p-8">
                        <h2 className="text-3xl font-bold mb-2 text-center">
                            {isLogin ? 'Welcome Back' : 'Create Account'}
                        </h2>
                        <p className="text-gray-400 text-center mb-8">
                            {isLogin ? 'Login to access your voice agents' : 'Register to get started with NextGen Voice'}
                        </p>

                        {message.text && (
                            <div className={`flex items-center gap-2 p-4 rounded-lg ${message.type === 'success'
                                ? 'bg-green-500/10 border border-green-500/30 text-green-400'
                                : 'bg-red-500/10 border border-red-500/30 text-red-400'
                                }`}>
                                {message.type === 'success' ? (
                                    <CheckCircle className="w-5 h-5" />
                                ) : (
                                    <XCircle className="w-5 h-5" />
                                )}
                                <span className="text-sm">{message.text}</span>
                            </div>
                        )}

                        <form onSubmit={handleSubmit} className="space-y-6">
                            <div>
                                <label className="block text-sm font-medium mb-2">Email</label>
                                <div className="relative">
                                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                                    <input
                                        type="email"
                                        name="email"
                                        value={formData.email}
                                        onChange={handleChange}
                                        className="w-full bg-gray-800/50 border border-gray-700 rounded-lg pl-11 pr-4 py-3 focus:outline-none focus:border-green-500 transition"
                                        placeholder="you@example.com"
                                        required
                                        disabled={loading}
                                    />
                                </div>
                            </div>

                            {!isLogin && (
                                <div>
                                    <label className="block text-sm font-medium mb-2">Name</label>
                                    <div className="relative">
                                        <input
                                            type="text"
                                            name="name"
                                            value={formData.name}
                                            onChange={handleChange}
                                            className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-4 py-3 focus:outline-none focus:border-green-500 transition"
                                            placeholder="Your name"
                                            required
                                            disabled={loading}
                                        />
                                    </div>
                                </div>
                            )}

                            <div>
                                <label className="block text-sm font-medium mb-2">Password</label>
                                <div className="relative">
                                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                                    <input
                                        type="password"
                                        name="password"
                                        value={formData.password}
                                        onChange={handleChange}
                                        className="w-full bg-gray-800/50 border border-gray-700 rounded-lg pl-11 pr-4 py-3 focus:outline-none focus:border-green-500 transition"
                                        placeholder="••••••••"
                                        required
                                        disabled={loading}
                                    />
                                </div>
                            </div>

                            {!isLogin && (
                                <div>
                                    <label className="block text-sm font-medium mb-2">Confirm Password</label>
                                    <div className="relative">
                                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                                        <input
                                            type="password"
                                            name="confirmPassword"
                                            value={formData.confirmPassword}
                                            onChange={handleChange}
                                            className="w-full bg-gray-800/50 border border-gray-700 rounded-lg pl-11 pr-4 py-3 focus:outline-none focus:border-green-500 transition"
                                            placeholder="••••••••"
                                            required
                                            disabled={loading}
                                        />
                                    </div>
                                </div>
                            )}

                            {isLogin && (
                                <div className="flex justify-end">
                                    <a href="#" className="text-sm text-green-500 hover:text-green-400 transition">
                                        Forgot password?
                                    </a>
                                </div>
                            )}

                            <button
                                type="submit"
                                disabled={loading}
                                className="w-full bg-green-500 hover:bg-green-600 text-white font-medium py-3 rounded-lg transition shadow-lg shadow-green-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {loading ? 'Processing...' : (isLogin ? 'Login' : 'Register')}
                            </button>
                        </form>

                        <div className="mt-6 text-center">
                            <p className="text-gray-400 text-sm">
                                {isLogin ? "Don't have an account? " : "Already have an account? "}
                                <button
                                    onClick={() => setIsLogin(!isLogin)}
                                    className="text-green-500 hover:text-green-400 transition font-medium"
                                >
                                    {isLogin ? 'Register' : 'Login'}
                                </button>
                            </p>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    )
}

export default Login
