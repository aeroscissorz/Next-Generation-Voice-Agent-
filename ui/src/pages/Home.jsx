import { useNavigate } from 'react-router-dom'
import { Headphones, CreditCard } from 'lucide-react'
import SpotlightCard from '../components/SpotlightCard'
import DotGrid from '../components/DotGrid'

function Home() {
    const navigate = useNavigate()

    return (
        <div className="min-h-screen bg-black text-white relative">
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

            {/* Multiple gradient layers for depth */}
            <div className="fixed top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1000px] h-[1000px] bg-gradient-radial from-green-500/20 via-green-500/5 to-transparent blur-3xl pointer-events-none"></div>
            <div className="fixed top-2/3 left-1/4 w-[600px] h-[600px] bg-gradient-radial from-emerald-500/15 to-transparent blur-3xl pointer-events-none"></div>
            <div className="fixed top-1/2 right-1/4 w-[500px] h-[500px] bg-gradient-radial from-teal-500/10 to-transparent blur-3xl pointer-events-none"></div>

            {/* Navigation */}
            <nav className="relative z-10 flex items-center justify-center px-8 py-8">
                <div className="flex items-center justify-between w-full max-w-4xl px-8 py-4 rounded-full border border-gray-800 bg-gray-900/50 backdrop-blur-sm">
                    <div className="flex items-center gap-2">
                        <div className="text-xl font-bold">NextGen Voice</div>
                    </div>

                    <div className="flex items-center gap-8 text-sm">
                        <a href="#features" className="hover:text-green-500 transition">Features</a>
                        <a href="#about" className="hover:text-green-500 transition">About</a>
                    </div>
                </div>
            </nav>

            {/* Hero Section */}
            <main className="relative z-10 overflow-hidden min-h-screen">

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
                            className="px-6 py-3 text-sm font-medium bg-green-500 hover:bg-green-600 rounded-full transition shadow-lg shadow-green-500/20 cursor-pointer"
                        >
                            Login
                        </button>
                    </div>

                    {/* Feature Cards */}
                    <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto mt-16">
                        <SpotlightCard
                            className="text-left hover:border-green-500/50 transition"
                            spotlightColor="rgba(34, 197, 94, 0.3)"
                        >
                            <Headphones className="text-green-500 w-10 h-10 mb-4" />
                            <h3 className="text-xl font-semibold mb-3">Support Agent</h3>
                            <p className="text-gray-400 text-sm">
                                Handle customer inquiries, troubleshoot issues, and provide instant support with natural voice interactions.
                            </p>
                        </SpotlightCard>

                        <SpotlightCard
                            className="text-left hover:border-green-500/50 transition"
                            spotlightColor="rgba(34, 197, 94, 0.3)"
                        >
                            <CreditCard className="text-green-500 w-10 h-10 mb-4" />
                            <h3 className="text-xl font-semibold mb-3">Billing Agent</h3>
                            <p className="text-gray-400 text-sm">
                                Process payments, check account balances, and manage billing inquiries through conversational AI.
                            </p>
                        </SpotlightCard>
                    </div>
                </div>
            </main>
        </div>
    )
}

export default Home
