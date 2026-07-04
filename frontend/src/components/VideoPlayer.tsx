"use client";

export default function VideoPlayer({ src }: { src: string }) {
  return (
    <video controls className="w-full rounded-xl border" src={src}>
      Your browser does not support the video tag.
    </video>
  );
}
