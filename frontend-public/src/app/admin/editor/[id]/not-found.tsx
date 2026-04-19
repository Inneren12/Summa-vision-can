import Link from 'next/link';

export default function EditorNotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
      <h2 className="text-xl">Publication not found</h2>
      <Link href="/admin" className="text-accent hover:underline">
        Back to list
      </Link>
    </div>
  );
}
