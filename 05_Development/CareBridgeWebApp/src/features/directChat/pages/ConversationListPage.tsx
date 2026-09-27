import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listMyConversations } from '../services/directChatApi';
import type { DirectConversationSummary } from '../models/directConversation';

export default function ConversationListPage() {
  const navigate = useNavigate();
  const [conversations, setConversations] = useState<DirectConversationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listMyConversations()
      .then(setConversations)
      .catch((e) => setError(`Lỗi tải danh sách cuộc trò chuyện: ${e}`))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8 text-center text-outline">Đang tải cuộc trò chuyện...</div>;

  return (
    <div className="p-8 font-sans">
      {/* Header */}
      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="text-[26px] font-bold text-on-surface m-0">Trò chuyện trực tiếp</h1>
          <p className="text-on-surface-variant text-sm mt-1">
            Kênh tư vấn &amp; trao đổi trực tiếp 1-1 giữa chuyên gia y tế và mẹ bầu
          </p>
        </div>
      </div>

      {error && (
        <div className="bg-error-container rounded-2xl p-4 mb-4 text-error text-sm">{error}</div>
      )}

      {/* Conversation List */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {conversations.length === 0 && !error && (
          <div className="bg-surface rounded-2xl p-12 text-center text-outline shadow-md">
            <span className="material-symbols-outlined text-4xl block mb-2 opacity-40">chat_bubble</span>
            <p className="text-sm font-semibold text-on-surface mb-1">Chưa có cuộc trò chuyện nào</p>
            <p className="text-xs text-outline">
              Các cuộc tư vấn sau khi được chấp nhận sẽ hiển thị danh sách nhắn tin tại đây.
            </p>
          </div>
        )}

        {conversations.map((c) => {
          const isMother = c.counterpartRole === 'MOTHER';
          const displayName = c.counterpartDisplayName || (isMother ? 'Mẹ bầu CareBridge' : 'Chuyên gia tư vấn');
          const initial = (displayName || (isMother ? 'M' : 'E'))[0]?.toUpperCase() || 'M';

          return (
            <div
              key={c.conversationId}
              onClick={() => navigate(`/expert/direct-chats/${c.conversationId}`)}
              className="bg-surface rounded-2xl p-5 shadow-md flex items-center justify-between hover:shadow-lg transition-shadow cursor-pointer"
            >
              <div className="flex items-center gap-4 min-w-0">
                <div className="w-12 h-12 rounded-full bg-primary-container text-primary font-bold text-sm flex items-center justify-center shrink-0 overflow-hidden">
                  {c.counterpartAvatarUrl ? (
                    <img src={c.counterpartAvatarUrl} alt={displayName} className="w-full h-full object-cover" />
                  ) : (
                    initial
                  )}
                </div>

                <div className="flex items-center gap-2 min-w-0">
                  <h3 className="font-bold text-base text-on-surface m-0 truncate">
                    {displayName}
                  </h3>
                  <span className="py-0.5 px-3 rounded-full text-xs font-semibold bg-[#E6F4EA] text-[#137333] shrink-0">
                    Đang mở
                  </span>
                </div>
              </div>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  navigate(`/expert/direct-chats/${c.conversationId}`);
                }}
                className="flex items-center justify-center gap-2 py-2.5 px-6 rounded-full bg-primary text-on-primary text-sm font-semibold hover:brightness-110 cursor-pointer whitespace-nowrap shrink-0 transition-all shadow-sm"
              >
                <span className="material-symbols-outlined text-base">forum</span>
                Vào tin nhắn
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

