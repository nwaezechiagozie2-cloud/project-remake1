"use client";
import Link from "next/link";
import React from 'react';
import { ArrowRight, Zap, Shield, MessageSquare, Plus } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white text-gray-900 selection:bg-emerald-700/10 selection:text-emerald-700">
      
      {/* Navigation */}
      <nav className="flex items-center justify-between max-w-[1200px] mx-auto px-8 py-8">
        <div className="flex items-center gap-3 group cursor-pointer">
          <div className="w-9 h-9 bg-[#09090b] rounded-xl flex items-center justify-center font-black text-white text-[15px] shadow-[0_4px_12px_rgba(9,9,11,0.3)] group-hover:scale-105 transition-transform">O</div>
          <span className="font-bold text-[18px] tracking-tight text-gray-900">OmniClose</span>
        </div>
        
        <div className="hidden md:flex items-center gap-10 text-[13.5px] font-semibold text-gray-500">
          <a href="#features" className="hover:text-gray-900 transition-colors">Features</a>
          <a href="#pricing" className="hover:text-gray-900 transition-colors">Pricing</a>
          <a href="#docs" className="hover:text-gray-900 transition-colors">Documentation</a>
        </div>

        <div className="flex items-center gap-5">
          <Link href="/login" className="text-[13.5px] font-bold text-gray-500 hover:text-gray-900 transition-colors">
            Sign in
          </Link>
          <Link href="/register">
            <button className="bg-gray-900 text-white text-[13.5px] font-bold px-6 py-2.5 rounded-xl hover:bg-black active:scale-95 transition-all shadow-sm">
              Get started
            </button>
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="max-w-[1200px] mx-auto px-8 pt-24 pb-32 text-center">
        <div className="inline-flex items-center gap-2.5 bg-gray-50 border border-gray-100 rounded-full px-4 py-1.5 text-[12px] font-bold text-gray-900 mb-12 shadow-sm animate-in fade-in slide-in-from-bottom-4 duration-1000">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-700 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-700"></span>
          </span>
          WhatsApp v2.0 is now live
        </div>

        <h1 className="text-[72px] md:text-[92px] font-black tracking-[-0.05em] text-gray-900 leading-[0.98] max-w-4xl mx-auto mb-10 translate-y-[-1px]">
          Close deals faster<br />
          <span className="text-gray-300">with WhatsApp AI.</span>
        </h1>

        <p className="text-[19px] text-gray-500 font-medium max-w-2xl mx-auto mb-14 leading-relaxed">
          The high-density operations platform for modern vendors. Automate inquiries, handle hand-offs, and track orders in one clean, powerful interface.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-24">
          <Link href="/register">
            <button className="w-full sm:w-auto bg-gray-900 text-white px-10 py-4 rounded-2xl font-bold text-[16px] hover:bg-black hover:shadow-[0_8px_30px_rgba(0,0,0,0.1)] hover:-translate-y-0.5 active:translate-y-0 transition-all">
              Build your shop
            </button>
          </Link>
          <button className="w-full sm:w-auto bg-white text-emerald-700 px-10 py-4 rounded-2xl font-bold text-[16px] border border-emerald-700/20 hover:border-emerald-700/40 transition-all">
            See how it works
          </button>
        </div>

        {/* Dense Detail Ribbon */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-[900px] mx-auto text-left py-12 border-y border-gray-100">
          <div className="space-y-3">
             <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center">
                <Zap size={15} className="text-emerald-700" />
             </div>
             <p className="text-[14px] font-bold text-gray-900">Instant AI Replies</p>
             <p className="text-[13px] text-gray-500 font-medium leading-relaxed">The bot handles 90% of product inquiries so you can focus on making sales.</p>
          </div>
          <div className="space-y-3">
             <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center">
                <Shield size={15} className="text-emerald-500" />
             </div>
             <p className="text-[14px] font-bold text-gray-900">Secure Checkout</p>
             <p className="text-[13px] text-gray-500 font-medium leading-relaxed">Automated account detail sharing and payment verification logs.</p>
          </div>
          <div className="space-y-3">
             <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
                <MessageSquare size={15} className="text-gray-600" />
             </div>
             <p className="text-[14px] font-bold text-gray-900">Smart Handoff</p>
             <p className="text-[13px] text-gray-500 font-medium leading-relaxed">AI notifies you only when a customer is ready to pay or needs human help.</p>
          </div>
        </div>

        {/* Dashboard Preview Overlay */}
        <div className="mt-32 relative group">
          <div className="absolute inset-0 bg-gradient-to-b from-transparent to-white/50 pointer-events-none z-10" />
          <div className="bg-white rounded-[40px] p-2 shadow-[0_0_0_1px_rgba(0,0,0,.04),0_32px_80px_-16px_rgba(0,0,0,.15)] border border-gray-100/50">
            <div className="bg-gray-50/50 rounded-[34px] border border-gray-100 overflow-hidden min-h-[500px] relative">
               {/* Mock UI Frame */}
               <div className="absolute top-0 left-0 w-64 h-full border-r border-gray-100 flex flex-col p-6 items-start">
                  <div className="w-8 h-8 bg-[#09090b] rounded-lg mb-6 shadow-sm"></div>
                  <div className="w-full h-8 bg-white border border-gray-100 rounded-lg mb-2 shadow-sm"></div>
                  <div className="w-full h-8 bg-gray-100 rounded-lg mb-2 opacity-50"></div>
                  <div className="w-full h-8 bg-gray-100 rounded-lg mb-2 opacity-30"></div>
               </div>
               <div className="ml-64 p-10 flex flex-col">
                  <div className="w-48 h-10 bg-gray-200 rounded-xl mb-12 opacity-40"></div>
                  <div className="grid grid-cols-2 gap-6 mb-12">
                     <div className="h-32 bg-white border border-gray-100 rounded-2xl shadow-sm"></div>
                     <div className="h-32 bg-gray-900 rounded-2xl shadow-lg"></div>
                  </div>
                  <div className="h-48 bg-white border border-gray-100 rounded-2xl shadow-sm"></div>
               </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer / CTA section */}
      <footer className="bg-gray-50 py-24 border-t border-gray-100">
        <div className="max-w-[700px] mx-auto text-center px-8">
           <h2 className="text-[32px] font-black tracking-tight text-gray-900 mb-6">Built for vendors who value speed.</h2>
           <p className="text-[16px] text-gray-500 font-medium mb-10 leading-relaxed">Stop wasting time answering "how much" and manual follow-ups. Start selling on autopilot today.</p>
           <Link href="/register">
             <button className="bg-gray-900 text-white px-10 py-4 rounded-2xl font-bold text-[16px] hover:bg-black transition-all flex items-center gap-2 mx-auto">
                Get Started Now <ArrowRight size={18} />
             </button>
           </Link>
        </div>
      </footer>
    </div>
  );
}
