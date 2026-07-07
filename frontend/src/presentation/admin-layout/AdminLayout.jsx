export default function AdminLayout({ children }) {
  return (
    <div className="admin-wrap">
      <main className="admin-main">
        <div className="admin-content">{children}</div>
      </main>
    </div>
  );
}
