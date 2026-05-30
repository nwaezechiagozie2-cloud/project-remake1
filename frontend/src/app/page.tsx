"use client";
import Link from "next/link";
import React from 'react';
import { ArrowRight, MessageSquare, ShieldCheck, BellRing } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-white via-[#EFF1FE]/50 to-[#DEDAF0]/45 text-gray-900 selection:bg-[#3B5EE4]/10 selection:text-[#3B5EE4] relative overflow-hidden">

      {/* Accent gradient orbs */}
      <div className="absolute top-[200px] right-[-180px] w-[640px] h-[640px] rounded-full bg-[#C5BFEC]/35 blur-3xl pointer-events-none" />
      <div className="absolute top-[820px] left-[-120px] w-[520px] h-[520px] rounded-full bg-[#C5BFEC]/30 blur-3xl pointer-events-none" />

      {/* Navigation */}
      <nav className="relative flex items-center justify-between max-w-[1200px] mx-auto px-8 py-8">
        <div className="flex items-center gap-3 group cursor-pointer">
          <div className="w-9 h-9 bg-[#09090b] rounded-xl flex items-center justify-center font-black text-white text-[15px] shadow-[0_4px_12px_rgba(9,9,11,0.3)] group-hover:scale-105 transition-transform">O</div>
          <span className="font-bold text-[18px] tracking-tight text-gray-900">OmniClose</span>
        </div>

        <div className="hidden md:flex items-center gap-10 text-[13.5px] font-semibold text-gray-500">
          <a href="#features" className="hover:text-gray-900 transition-colors">Features</a>
          <a href="#pricing" className="hover:text-gray-900 transition-colors">Pricing</a>
          <a href="#docs" className="hover:text-gray-900 transition-colors">Docs</a>
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
      <main className="relative max-w-[1100px] mx-auto px-8 pt-16 pb-32 text-center">
        <div className="inline-flex items-center gap-2.5 bg-white/80 backdrop-blur border border-gray-100 rounded-full px-4 py-1.5 text-[12px] font-bold text-gray-700 mb-10 shadow-sm">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#3B5EE4] opacity-60"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#3B5EE4]"></span>
          </span>
          Works with WhatsApp &amp; Instagram DMs
        </div>

        <h1 className="text-[64px] md:text-[88px] font-black tracking-[-0.045em] text-gray-900 leading-[1] max-w-4xl mx-auto mb-8">
          Never miss a<br />
          <span className="text-[#3B5EE4]">customer chat</span> again.
        </h1>

        <p className="text-[18px] text-gray-500 font-medium max-w-xl mx-auto mb-12 leading-relaxed">
          An AI receptionist that answers questions, shares your catalogue,
          and pings you only when a customer is ready to pay.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mb-20">
          <Link href="/register">
            <button className="w-full sm:w-auto bg-gray-900 text-white px-8 py-3.5 rounded-2xl font-bold text-[15px] hover:bg-black hover:shadow-[0_8px_30px_rgba(0,0,0,0.12)] hover:-translate-y-0.5 active:translate-y-0 transition-all flex items-center gap-2">
              Set up your bot <ArrowRight size={16} />
            </button>
          </Link>
          <a href="#features" className="w-full sm:w-auto bg-white text-gray-900 px-8 py-3.5 rounded-2xl font-bold text-[15px] border border-gray-200 hover:border-gray-300 transition-all">
            See what it does
          </a>
        </div>

        {/* Floating chat bubble decoration */}
        <div className="relative max-w-[760px] mx-auto h-[260px] mb-16">
          <div className="absolute left-[8%] top-2 rotate-[-3deg] bg-white border border-gray-100 rounded-2xl rounded-bl-sm shadow-[0_8px_24px_rgba(0,0,0,0.06)] px-5 py-3 text-left max-w-[260px]">
            <p className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-1">Customer · 10:42</p>
            <p className="text-[13.5px] font-semibold text-gray-800 leading-snug">Hi, do you have the brown leather bag in stock? How much?</p>
          </div>

          <div className="absolute right-[6%] top-[70px] rotate-[2deg] bg-gradient-to-br from-[#5571E8] to-[#2B4DD0] text-white rounded-2xl rounded-br-sm shadow-[0_12px_28px_rgba(59,94,228,0.18)] px-5 py-3 text-left max-w-[290px]">
            <p className="text-[11px] font-bold text-white/70 uppercase tracking-wider mb-1">AI · 10:42</p>
            <p className="text-[13.5px] font-semibold leading-snug">Hey! Yes, the brown leather bag is in stock, ₦15,000. Want me to send the payment details?</p>
          </div>

          <div className="absolute left-[14%] bottom-0 rotate-[-1deg] bg-white border border-[#E0E5FB] rounded-2xl rounded-bl-sm shadow-[0_8px_24px_rgba(0,0,0,0.06)] px-5 py-3 text-left max-w-[230px]">
            <p className="text-[11px] font-bold text-[#3B5EE4] uppercase tracking-wider mb-1">Owner · You</p>
            <p className="text-[13.5px] font-semibold text-gray-800 leading-snug"> Approved, send the account details.</p>
          </div>
        </div>

        {/* Honest feature ribbon */}
        <div id="features" className="grid grid-cols-1 md:grid-cols-3 gap-10 max-w-[900px] mx-auto text-left py-14 border-y border-gray-100">
          <div className="space-y-3">
            <div className="w-9 h-9 rounded-xl bg-[#EFF1FE] flex items-center justify-center">
              <MessageSquare size={16} className="text-[#3B5EE4]" strokeWidth={2.2} />
            </div>
            <p className="text-[15px] font-bold text-gray-900">Answers in seconds</p>
            <p className="text-[13.5px] text-gray-500 font-medium leading-relaxed">
              The bot reads your catalogue and business info to reply to inquiries the moment they land, even when you&apos;re asleep.
            </p>
          </div>
          <div className="space-y-3">
            <div className="w-9 h-9 rounded-xl bg-[#EFF1FE] flex items-center justify-center">
              <ShieldCheck size={16} className="text-[#3B5EE4]" strokeWidth={2.2} />
            </div>
            <p className="text-[15px] font-bold text-gray-900">You approve payments</p>
            <p className="text-[13.5px] text-gray-500 font-medium leading-relaxed">
              When a customer is ready to pay, the bot asks you first. Your bank details only go out after you tap approve.
            </p>
          </div>
          <div className="space-y-3">
            <div className="w-9 h-9 rounded-xl bg-[#EFF1FE] flex items-center justify-center">
              <BellRing size={16} className="text-[#3B5EE4]" strokeWidth={2.2} />
            </div>
            <p className="text-[15px] font-bold text-gray-900">Quiet by default</p>
            <p className="text-[13.5px] text-gray-500 font-medium leading-relaxed">
              No more 50 unread chats. The AI handles the &quot;how much?&quot; loop and only buzzes you for the moments that matter.
            </p>
          </div>
        </div>
      </main>

      {/* Footer / CTA section */}
      <footer className="relative bg-gradient-to-b from-white to-[#EFF1FE]/70 py-24 border-t border-gray-100">
        <div className="max-w-[680px] mx-auto text-center px-8">
          <h2 className="text-[34px] font-black tracking-tight text-gray-900 mb-5">Sell while you sleep.</h2>
          <p className="text-[15.5px] text-gray-500 font-medium mb-9 leading-relaxed">
            Upload your catalogue once. Let the AI handle the typing.
          </p>
          <Link href="/register">
            <button className="bg-gray-900 text-white px-9 py-3.5 rounded-2xl font-bold text-[15px] hover:bg-black transition-all flex items-center gap-2 mx-auto">
              Get started, it&apos;s free <ArrowRight size={16} />
            </button>
          </Link>
        </div>
      </footer>
    </div>
  );
}
