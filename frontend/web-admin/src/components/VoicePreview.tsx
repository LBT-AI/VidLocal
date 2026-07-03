"use client";

export default function VoicePreview({ src }: { src: string }) {
  return <audio controls className="w-full" src={src} />;
}
