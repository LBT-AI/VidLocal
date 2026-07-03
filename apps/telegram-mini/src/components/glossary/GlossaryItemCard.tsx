import React from "react";
import { GlossaryEntry } from "../../types";
import { IOSCard } from "../ui/IOSCard";
import { Edit2, Trash2, User } from "lucide-react";

interface GlossaryItemCardProps {
  key?: React.Key;
  entry: GlossaryEntry;
  onEdit?: () => void | Promise<void>;
  onDelete?: () => void | Promise<void>;
  id?: string;
}

export function GlossaryItemCard({ entry, onEdit, onDelete, id }: GlossaryItemCardProps) {
  return (
    <IOSCard id={id || `glossary-card-${entry.id}`} className="space-y-3 border-white/[0.08]">
      {/* Name and actions */}
      <div className="flex justify-between items-start gap-2">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
            <User className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-white tracking-tight">
              {entry.source_name}
            </h4>
            <p className="text-[10px] text-purple-400 uppercase tracking-wider font-semibold">
              → {entry.target_name}
            </p>
          </div>
        </div>

        {/* Action button triggers */}
        <div className="flex gap-1.5">
          {onEdit && (
            <button
              onClick={onEdit}
              className="p-1.5 rounded-lg bg-white/[0.04] border border-white/[0.08] text-slate-400 hover:text-white transition-colors"
            >
              <Edit2 className="w-3.5 h-3.5" />
            </button>
          )}
          {onDelete && (
            <button
              onClick={onDelete}
              className="p-1.5 rounded-lg bg-red-500/10 border border-red-500/25 text-red-400 hover:bg-red-500/20 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Grid of information */}
      <div className="grid grid-cols-2 gap-2 pt-1 border-t border-white/[0.04] text-[11px] leading-tight">
        {entry.role && (
          <div>
            <span className="text-slate-500 block">Vai trò:</span>
            <span className="text-slate-300 font-medium">{entry.role}</span>
          </div>
        )}
        {entry.gender && (
          <div>
            <span className="text-slate-500 block">Giới tính:</span>
            <span className="text-slate-300 font-medium">{entry.gender}</span>
          </div>
        )}
        {entry.aliases && (
          <div className="col-span-2">
            <span className="text-slate-500 block">Tên gọi khác / Aliases:</span>
            <span className="text-slate-300">{entry.aliases}</span>
          </div>
        )}
        {entry.pronoun_style && (
          <div>
            <span className="text-slate-500 block">Xưng hô:</span>
            <span className="text-purple-300 font-mono font-medium">{entry.pronoun_style}</span>
          </div>
        )}
        {entry.family_clan && (
          <div>
            <span className="text-slate-500 block">Gia tộc:</span>
            <span className="text-slate-300">{entry.family_clan}</span>
          </div>
        )}
      </div>

      {entry.notes && (
        <div className="bg-white/[0.02] p-2 rounded-xl text-[11px] text-slate-400 border border-white/[0.04]">
          <span className="text-slate-500 font-bold block mb-0.5 uppercase tracking-wide text-[9px]">Ghi chú:</span>
          <p className="italic leading-snug">{entry.notes}</p>
        </div>
      )}
    </IOSCard>
  );
}
