import { Routes, Route } from "react-router-dom";

import Navbar from "./presentation/common/Navbar.jsx";
import ProtectedRoute from "./presentation/common/ProtectedRoute.jsx";
import Landing from "./presentation/landing-home/Landing.jsx";
import Home from "./presentation/landing-home/Home.jsx";
import ListingDetail from "./presentation/listing-detail/ListingDetail.jsx";
import Login from "./presentation/auth/Login.jsx";
import MFAVerify from "./presentation/mfa-verify/MFAVerify.jsx";
import Register from "./presentation/auth/Register.jsx";
import VerifyEmail from "./presentation/verify-email/VerifyEmail.jsx";
import ForgotPassword from "./presentation/password-reset/ForgotPassword.jsx";
import ResetPassword from "./presentation/password-reset/ResetPassword.jsx";
import AcceptInvite from "./presentation/common/AcceptInvite.jsx";
import Dashboard from "./presentation/dashboard/Dashboard.jsx";
import AccountSettings from "./presentation/account-settings/AccountSettings.jsx";
import Checkout from "./presentation/checkout/Checkout.jsx";
import OrderDetail from "./presentation/order-detail/OrderDetail.jsx";
import AdminOverview from "./presentation/overview/AdminOverview.jsx";
import AdminLiveMonitor from "./presentation/live-monitor/AdminLiveMonitor.jsx";
import AdminListings from "./presentation/listings/AdminListings.jsx";
import AdminCreate from "./presentation/listings/AdminCreate.jsx";
import AdminUsers from "./presentation/users/AdminUsers.jsx";
import AdminOrders from "./presentation/orders/AdminOrders.jsx";
import AdminAuditLog from "./presentation/audit-log/AdminAuditLog.jsx";
import NotFound from "./presentation/common/NotFound.jsx";

export default function App() {
  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route
          path="/auctions"
          element={
            <ProtectedRoute>
              <Home />
            </ProtectedRoute>
          }
        />
        <Route
          path="/listings/:id"
          element={
            <ProtectedRoute>
              <ListingDetail />
            </ProtectedRoute>
          }
        />
        <Route path="/login" element={<Login />} />
        <Route path="/mfa-verify" element={<MFAVerify />} />
        <Route path="/register" element={<Register />} />
        <Route path="/verify-email" element={<VerifyEmail />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/accept-invite" element={<AcceptInvite />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/account-settings"
          element={
            <ProtectedRoute>
              <AccountSettings />
            </ProtectedRoute>
          }
        />
        <Route
          path="/checkout/:orderId"
          element={
            <ProtectedRoute>
              <Checkout />
            </ProtectedRoute>
          }
        />
        <Route
          path="/orders/:orderId"
          element={
            <ProtectedRoute>
              <OrderDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/overview"
          element={
            <ProtectedRoute requireAdmin>
              <AdminOverview />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/live-monitor"
          element={
            <ProtectedRoute requireAdmin>
              <AdminLiveMonitor />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/listings"
          element={
            <ProtectedRoute requireAdmin>
              <AdminListings />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/add-item"
          element={
            <ProtectedRoute requireAdmin>
              <AdminCreate />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/users"
          element={
            <ProtectedRoute requireAdmin>
              <AdminUsers />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/orders"
          element={
            <ProtectedRoute requireAdmin>
              <AdminOrders />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/audit-log"
          element={
            <ProtectedRoute requireAdmin>
              <AdminAuditLog />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </>
  );
}
