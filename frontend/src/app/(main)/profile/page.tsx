"use client";
import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, KeyRound, Loader2, Mail, ShieldCheck, UserCircle } from "lucide-react";
import {
  changePassword,
  confirmEmailChange,
  confirmEmailVerification,
  fetchVendorProfile,
  getApiErrorMessage,
  requestEmailChange,
  requestEmailVerification,
  updateVendorProfile,
  type VendorProfile,
} from "@/lib/api";

export default function ProfilePage() {
  const [profile, setProfile] = useState<VendorProfile | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [verifyToken, setVerifyToken] = useState("");
  const [emailChangeToken, setEmailChangeToken] = useState("");
  const [passwords, setPasswords] = useState({ current: "", next: "" });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const auth = useCallback(async () => {
    const vendorId = localStorage.getItem("otc_vendor_id");
    const token = localStorage.getItem("otc_token");
    if (!vendorId || !token) return null;
    return { vendorId, token };
  }, []);

  const loadProfile = useCallback(async () => {
    try {
      const credentials = await auth();
      if (!credentials) return;
      const loaded = await fetchVendorProfile(credentials.vendorId, credentials.token);
      setProfile(loaded);
      setDisplayName(loaded.name || "");
      setError("");
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to load profile"));
    } finally {
      setLoading(false);
    }
  }, [auth]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("verify_token");
    const purpose = params.get("purpose");
    if (token && purpose) {
      if (purpose === "REGISTER_EMAIL") {
        setVerifyToken(token);
      }
      if (purpose === "EMAIL_CHANGE") {
        setEmailChangeToken(token);
      }
      window.history.replaceState({}, "", "/profile");
    }
    loadProfile();
  }, [loadProfile]);

  async function handleResendVerification() {
    if (!profile) return;
    setSaving("verify-request");
    setError("");
    setMessage("");
    try {
      const data = await requestEmailVerification(profile.email);
      setMessage(data?.email_verification?.verification_token
        ? `Verification token: ${data.email_verification.verification_token}`
        : "Verification email requested.");
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to request verification"));
    } finally {
      setSaving("");
    }
  }

  async function handleUpdateProfile() {
    const credentials = await auth();
    if (!credentials || !displayName.trim()) return;
    setSaving("profile");
    setError("");
    setMessage("");
    try {
      const updated = await updateVendorProfile(credentials.vendorId, credentials.token, displayName.trim());
      setProfile(updated);
      setDisplayName(updated.name || "");
      setMessage("Profile updated.");
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to update profile"));
    } finally {
      setSaving("");
    }
  }

  async function handleConfirmVerification() {
    if (!verifyToken.trim()) return;
    setSaving("verify-confirm");
    setError("");
    setMessage("");
    try {
      await confirmEmailVerification(verifyToken.trim());
      setVerifyToken("");
      setMessage("Email verified.");
      await loadProfile();
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to verify email"));
    } finally {
      setSaving("");
    }
  }

  async function handleRequestEmailChange() {
    const credentials = await auth();
    if (!credentials || !newEmail.trim()) return;
    setSaving("email-request");
    setError("");
    setMessage("");
    try {
      const data = await requestEmailChange(credentials.vendorId, credentials.token, newEmail.trim());
      setMessage(data?.email_verification?.verification_token
        ? `Email-change token: ${data.email_verification.verification_token}`
        : "Email-change verification requested.");
      await loadProfile();
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to request email change"));
    } finally {
      setSaving("");
    }
  }

  async function handleConfirmEmailChange() {
    const credentials = await auth();
    if (!credentials || !emailChangeToken.trim()) return;
    setSaving("email-confirm");
    setError("");
    setMessage("");
    try {
      setProfile(await confirmEmailChange(credentials.vendorId, credentials.token, emailChangeToken.trim()));
      setEmailChangeToken("");
      setNewEmail("");
      setMessage("Email changed.");
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to confirm email change"));
    } finally {
      setSaving("");
    }
  }

  async function handleChangePassword() {
    const credentials = await auth();
    if (!credentials || !passwords.current || !passwords.next) return;
    setSaving("password");
    setError("");
    setMessage("");
    try {
      await changePassword(credentials.vendorId, credentials.token, passwords.current, passwords.next);
      setPasswords({ current: "", next: "" });
      setMessage("Password updated.");
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to change password"));
    } finally {
      setSaving("");
    }
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="animate-spin text-gray-400" size={32} />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto bg-white">
      <div className="max-w-[780px] px-8 pt-10 pb-16 mx-auto">
        <div className="mb-10">
          <p className="text-[11px] font-bold tracking-[0.12em] uppercase text-gray-400 mb-1">Account</p>
          <h1 className="text-[24px] font-bold tracking-[-0.02em] text-gray-900">Profile</h1>
          {error && <p className="mt-3 text-[12px] font-bold text-red-600">{error}</p>}
          {message && <p className="mt-3 text-[12px] font-bold text-[#3B5EE4]">{message}</p>}
        </div>

        <div className="space-y-10">
          <section className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
                <UserCircle size={16} className="text-gray-700" />
              </div>
              <h2 className="text-[14px] font-bold text-gray-900">Profile</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-3">
              <input
                value={displayName}
                onChange={event => setDisplayName(event.target.value)}
                placeholder="Your name"
                className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-2.5 text-[14px] focus:outline-none focus:ring-2 focus:ring-[#3B5EE4]/20"
              />
              <ActionButton loading={saving === "profile"} onClick={handleUpdateProfile}>Save profile</ActionButton>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {(["google", "instagram"] as const).map(provider => (
                <div key={provider} className="p-4 border border-gray-100 rounded-2xl bg-gray-50/40 flex items-center justify-between">
                  <div>
                    <p className="text-[13px] font-bold text-gray-900 capitalize">{provider}</p>
                    <p className="text-[12px] text-gray-400 font-medium">Login provider</p>
                  </div>
                  <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full ${profile?.providers?.[provider] ? "bg-[#EFF1FE] text-[#3B5EE4]" : "bg-gray-100 text-gray-500"}`}>
                    {profile?.providers?.[provider] ? "Connected" : "Not linked"}
                  </span>
                </div>
              ))}
            </div>
          </section>

          <section className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-[#EFF1FE] flex items-center justify-center">
                <Mail size={16} className="text-[#3B5EE4]" />
              </div>
              <h2 className="text-[14px] font-bold text-gray-900">Email</h2>
            </div>

            <div className="p-5 border border-gray-100 rounded-2xl bg-gray-50/40 flex items-center justify-between gap-4">
              <div>
                <p className="text-[13px] font-bold text-gray-900">{profile?.email}</p>
                <p className="text-[12px] text-gray-400 font-medium">
                  {profile?.email_verified ? "Verified email address" : "Email address is not verified"}
                </p>
              </div>
              <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full flex items-center gap-1.5 ${profile?.email_verified ? "bg-[#EFF1FE] text-[#3B5EE4]" : "bg-amber-50 text-amber-700"}`}>
                <CheckCircle2 size={13} />
                {profile?.email_verified ? "Verified" : "Unverified"}
              </span>
            </div>

            {!profile?.email_verified && (
              <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-3">
                <input
                  value={verifyToken}
                  onChange={event => setVerifyToken(event.target.value)}
                  placeholder="Verification token"
                  className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-2.5 text-[14px] focus:outline-none focus:ring-2 focus:ring-[#3B5EE4]/20"
                />
                <div className="flex gap-2">
                  <ActionButton loading={saving === "verify-request"} onClick={handleResendVerification}>Request token</ActionButton>
                  <ActionButton loading={saving === "verify-confirm"} onClick={handleConfirmVerification}>Verify</ActionButton>
                </div>
              </div>
            )}
          </section>

          <section className="space-y-4 pt-8 border-t border-gray-100">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
                <ShieldCheck size={16} className="text-gray-700" />
              </div>
              <h2 className="text-[14px] font-bold text-gray-900">Change Email</h2>
            </div>
            {profile?.pending_email && (
              <p className="text-[12px] text-amber-700 font-bold">Pending email: {profile.pending_email}</p>
            )}
            <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-3">
              <input
                type="email"
                name="otc-new-email-target"
                value={newEmail}
                onChange={event => setNewEmail(event.target.value)}
                placeholder="New email"
                autoComplete="off"
                autoCorrect="off"
                spellCheck={false}
                data-1p-ignore="true"
                data-lpignore="true"
                className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-2.5 text-[14px] focus:outline-none focus:ring-2 focus:ring-[#3B5EE4]/20"
              />
              <ActionButton loading={saving === "email-request"} onClick={handleRequestEmailChange}>Request change</ActionButton>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-3">
              <input
                value={emailChangeToken}
                onChange={event => setEmailChangeToken(event.target.value)}
                placeholder="Email-change token"
                className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-2.5 text-[14px] focus:outline-none focus:ring-2 focus:ring-[#3B5EE4]/20"
              />
              <ActionButton loading={saving === "email-confirm"} onClick={handleConfirmEmailChange}>Confirm change</ActionButton>
            </div>
          </section>

          <section className="space-y-4 pt-8 border-t border-gray-100">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
                <KeyRound size={16} className="text-gray-700" />
              </div>
              <h2 className="text-[14px] font-bold text-gray-900">Change Password</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <input
                type="password"
                value={passwords.current}
                onChange={event => setPasswords({ ...passwords, current: event.target.value })}
                placeholder="Current password"
                className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-2.5 text-[14px] focus:outline-none focus:ring-2 focus:ring-[#3B5EE4]/20"
              />
              <input
                type="password"
                value={passwords.next}
                onChange={event => setPasswords({ ...passwords, next: event.target.value })}
                placeholder="New password"
                className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-2.5 text-[14px] focus:outline-none focus:ring-2 focus:ring-[#3B5EE4]/20"
              />
            </div>
            <ActionButton loading={saving === "password"} onClick={handleChangePassword}>Update password</ActionButton>
          </section>
        </div>
      </div>
    </div>
  );
}

function ActionButton({ children, loading, onClick }: { children: React.ReactNode; loading: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading}
      className="bg-[#3B5EE4] shadow-lg shadow-[#3B5EE4]/15 text-white px-4 py-2.5 rounded-xl text-[12px] font-bold hover:bg-[#2B4DD0] hover:shadow-[#3B5EE4]/25 transition-colors disabled:opacity-50 flex items-center justify-center gap-2 whitespace-nowrap"
    >
      {loading && <Loader2 size={14} className="animate-spin" />}
      {children}
    </button>
  );
}
