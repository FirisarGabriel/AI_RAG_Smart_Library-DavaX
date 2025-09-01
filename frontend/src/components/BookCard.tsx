type BookCardProps = { title?: string; why?: string; summary?: string; };

export default function BookCard({ title, why, summary }: BookCardProps) {
  if (!title && !summary) return null;

  return (
    <div className="bookcard">
      {title && <h2>{title}</h2>}
      {why && (
        <p className="why">
          <span className="label">De ce:</span> {why}
        </p>
      )}
      {summary && <div className="summary">{summary}</div>}
    </div>
  );
}
