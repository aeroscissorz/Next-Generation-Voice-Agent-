import { useNavigate } from 'react-router-dom'
import { Headphones, CreditCard } from 'lucide-react'

function Home() {
    const navigate = useNavigate()

    return (
        <div className="min-h-screen bg-black text-white">
            {/* Navigation */}
            <nav className="flex items-center justify-between px-8 py-5 border-b border-gray-800">
                <div className="text-2xl font-bold">NextGen Voice</div>

                <div className="hidden md:flex items-center gap-8 text-sm">
                    <a href="#" className="hover:text-gray-300 transition">Features</a>
                    <a href="#" className="hover:text-gray-300 transition">Demo</a>
                    <a href="#" className="hover:text-gray-300 transition">Documentation</a>
                    <a href="#" className="hover:text-gray-300 transition">About</a>
                </div>

                <div className="flex items-center gap-4">
                    <button
                        onClick={() => navigate('/login')}
                        className="px-5 py-2 text-sm font-medium hover:text-gray-300 transition"
                    >
                        Login
                    </button>
                    <button
                        onClick={() => navigate('/login')}
                        className="px-5 py-2 text-sm font-medium bg-green-500 hover:bg-green-600 rounded-full transition"
                    >
                        Register
                    </button>
                </div>
            </nav>

            {/* Hero Section */}
            <main className="relative overflow-hidden min-h-screen">
                {/* Multiple gradient layers for depth */}
                <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1000px] h-[1000px] bg-gradient-radial from-green-500/20 via-green-500/5 to-transparent blur-3xl -z-10"></div>
                <div className="absolute top-2/3 left-1/4 w-[600px] h-[600px] bg-gradient-radial from-emerald-500/15 to-transparent blur-3xl -z-10"></div>
                <div className="absolute top-1/2 right-1/4 w-[500px] h-[500px] bg-gradient-radial from-teal-500/10 to-transparent blur-3xl -z-10"></div>

                {/* Enhanced dot pattern with varying opacity */}
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.05)_1px,transparent_1px)] bg-[length:20px_20px] -z-10"></div>
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(16,185,129,0.03)_1px,transparent_1px)] bg-[length:40px_40px] -z-10"></div>

                {/* Grid lines for futuristic effect */}
                <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[length:100px_100px] -z-10"></div>

                <div className="max-w-6xl mx-auto px-8 py-20 text-center relative z-10">
                    <div className="mb-6">
                        <span className="text-sm tracking-wider text-gray-400">INTELLIGENT </span>
                        <span className="text-sm tracking-wider text-green-500">SUPPORT & BILLING</span>
                    </div>

                    <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight">
                        AI Voice Agents for<br />Support & Billing
                    </h1>

                    <p className="text-lg text-gray-400 mb-10 max-w-2xl mx-auto">
                        Experience the future of customer service with intelligent voice agents that handle support inquiries and billing operations seamlessly.
                    </p>

                    <div className="flex items-center justify-center gap-4 mb-20">
                        <button className="px-6 py-3 text-sm font-medium border border-gray-700 hover:border-gray-500 rounded-full transition">
                            View Demo
                        </button>
                        <button
                            onClick={() => navigate('/login')}
                            className="px-6 py-3 text-sm font-medium bg-green-500 hover:bg-green-600 rounded-full transition shadow-lg shadow-green-500/20"
                        >
                            Try it now
                        </button>
                    </div>

                    {/* Feature Cards */}
                    <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto mt-16">
                        <div className="bg-gray-900/50 backdrop-blur-sm border border-gray-800 rounded-lg p-8 text-left hover:border-green-500/50 transition">
                            <Headphones className="text-green-500 w-10 h-10 mb-4" />
                            <h3 className="text-xl font-semibold mb-3">Support Agent</h3>
                            <p className="text-gray-400 text-sm">
                                Handle customer inquiries, troubleshoot issues, and provide instant support with natural voice interactions.
                            </p>
                        </div>

                        <div className="bg-gray-900/50 backdrop-blur-sm border border-gray-800 rounded-lg p-8 text-left hover:border-green-500/50 transition">
                            <CreditCard className="text-green-500 w-10 h-10 mb-4" />
                            <h3 className="text-xl font-semibold mb-3">Billing Agent</h3>
                            <p className="text-gray-400 text-sm">
                                Process payments, check account balances, and manage billing inquiries through conversational AI.
                            </p>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    )
}

export default Home
