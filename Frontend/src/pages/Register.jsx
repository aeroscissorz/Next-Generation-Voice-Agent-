import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Mail, Lock, User, CheckCircle, XCircle } from 'lucide-react'
import DotGrid from '../components/DotGrid'
import { registerUser } from '../api'

function Register() {
    const navigate = useNavigate()
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
            // Validate passwords match
            if (formData.password !== formData.confirmPassword) {
                setMessage({ type: 'error', text: 'Passwords do not match' })
                setLoading(false)
                return
            }

            // Validate password strength
            if (formData.password.length < 6) {
                setMessage({ type: 'error', text: 'Password must be at least 6 characters' })
                setLoading(false)
                return
            }

            // Register using API module
            const result = await registerUser(formData.email, formData.name, formData.password)

            if (!result.success) {
                setMessage({ type: 'error', text: result.error })
            } else {
                setMessage({ type: 'success', text: 'Registration successful! Redirecting to login...' })
                setTimeout(() => navigate('/login'), 2000)
            }
        } catch (error) {
            console.error('Registration error:', error)
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
            <nav className="relative z-10 flex items-center justify-center px-8 py-8">
                <div className="flex items-center justify-between w-full max-w-4xl px-8 py-4 rounded-full border border-gray-800 bg-gray-900/50 backdrop-blur-sm">
                    <div className="flex items-center gap-2">
                        <div className="text-xl font-bold">NextGen Voice</div>
                    </div>

                    <div className="flex items-center gap-8 text-sm">
                        <a href="#features" className="hover:text-green-500 transition">Features</a>
                        <a href="#about" className="hover:text-green-500 transition">About</a>
                        <button
                            onClick={() => navigate('/')}
                            className="px-4 py-2 text-sm font-medium border border-gray-700 hover:border-gray-500 rounded-full transition"
                        >
                            Back to Home
                        </button>
                    </div>
                </div>
            </nav>

            {/* Register Form */}
            <main className="relative overflow-hidden min-h-screen flex items-center justify-center">
                {/* DotGrid Background */}
                <div className="fixed inset-0 w-full h-full">
                    <DotGrid
                        dotSize={10}
                        gap={15}
                        baseColor="#1a1a1a"
                        activeColor="#22c55e"
                        proximity={120}
                        shockRadius={250}
                        shockStrength={5}
                        resistance={750}
                        returnDuration={1.5}
                        className="w-full h-full"
                    />
                </div>

                {/* Gradient layers */}
                <div className="fixed top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1000px] h-[1000px] bg-gradient-radial from-green-500/20 via-green-500/5 to-transparent blur-3xl pointer-events-none"></div>
                <div className="fixed top-2/3 left-1/4 w-[600px] h-[600px] bg-gradient-radial from-emerald-500/15 to-transparent blur-3xl pointer-events-none"></div>
                <div className="fixed top-1/2 right-1/4 w-[500px] h-[500px] bg-gradient-radial from-teal-500/10 to-transparent blur-3xl pointer-events-none"></div>

                <div className="w-full max-w-md px-8 relative z-10">
                    <div className="bg-gray-900/50 backdrop-blur-sm border border-gray-800 rounded-2xl p-8">
                        <h2 className="text-3xl font-bold mb-2 text-center">
                            Create Your Account
                        </h2>
                        <p className="text-gray-400 text-center mb-8">
                            Join NextGen Voice and start building intelligent voice agents
                        </p>

                        {message.text && (
                            <div className={`flex items-center gap-2 p-4 rounded-lg mb-6 ${message.type === 'success'
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
                                <label className="block text-sm font-medium mb-2">Full Name</label>
                                <div className="relative">
                                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                                    <input
                                        type="text"
                                        name="name"
                                        value={formData.name}
                                        onChange={handleChange}
                                        className="w-full bg-gray-800/50 border border-gray-700 rounded-lg pl-11 pr-4 py-3 focus:outline-none focus:border-green-500 transition"
                                        placeholder="John Doe"
                                        required
                                        disabled={loading}
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-2">Email Address</label>
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
                                        minLength={6}
                                    />
                                </div>
                                <p className="text-xs text-gray-500 mt-1">Must be at least 6 characters</p>
                            </div>

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

                            <button
                                type="submit"
                                disabled={loading}
                                className="w-full bg-green-500 hover:bg-green-600 text-white font-medium py-3 rounded-lg transition shadow-lg shadow-green-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {loading ? 'Creating Account...' : 'Create Account'}
                            </button>
                        </form>

                        <div className="mt-6 text-center">
                            <p className="text-gray-400 text-sm">
                                Already have an account?{' '}
                                <button
                                    onClick={() => navigate('/login')}
                                    className="text-green-500 hover:text-green-400 transition font-medium"
                                >
                                    Login
                                </button>
                            </p>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    )
}

export default Register
