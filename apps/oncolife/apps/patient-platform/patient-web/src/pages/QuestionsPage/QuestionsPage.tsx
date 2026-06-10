/**
 * Questions Page
 * ==============
 * 
 * "Questions to Ask Doctor" feature for patients.
 * Allows patients to create, manage, and share questions with their physician.
 */

import React, { useState } from 'react';
import { 
  MessageCircleQuestion, 
  Plus, 
  Share2, 
  Edit3, 
  Trash2, 
  CheckCircle,
  Clock,
  Send,
  Eye,
  EyeOff
} from 'lucide-react';
import {
  QuestionsPageContainer,
  PageHeader,
  QuestionForm,
  QuestionInput,
  CategorySelect,
  ShareToggle,
  SubmitButton,
  QuestionsList,
  QuestionCard,
  Badge,
  ActionButton,
  EmptyState,
  FilterTabs,
  FilterTab,
  LoadingSpinner,
} from './QuestionsPage.styles';
import {
  useQuestions,
  useCreateQuestion,
  useUpdateQuestion,
  useDeleteQuestion,
  useToggleShare,
  type Question,
} from '../../services/questions';

type FilterType = 'all' | 'shared' | 'private' | 'answered';

const QuestionsPage: React.FC = () => {
  // State
  const [filter, setFilter] = useState<FilterType>('all');
  const [newQuestion, setNewQuestion] = useState('');
  const [newCategory, setNewCategory] = useState<'symptom' | 'medication' | 'treatment' | 'other'>('other');
  const [shareNew, setShareNew] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');

  // API hooks
  const { data, isLoading } = useQuestions();
  const createMutation = useCreateQuestion();
  const updateMutation = useUpdateQuestion();
  const deleteMutation = useDeleteQuestion();
  const shareMutation = useToggleShare();

  // Filter questions
  const filteredQuestions = React.useMemo(() => {
    if (!data?.questions) return [];
    
    return data.questions.filter(q => {
      switch (filter) {
        case 'shared':
          return q.share_with_physician;
        case 'private':
          return !q.share_with_physician;
        case 'answered':
          return q.is_answered;
        default:
          return true;
      }
    });
  }, [data?.questions, filter]);

  // Handlers
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newQuestion.trim()) return;

    await createMutation.mutateAsync({
      question_text: newQuestion.trim(),
      category: newCategory,
      share_with_physician: shareNew,
    });

    setNewQuestion('');
    setShareNew(false);
  };

  const handleToggleShare = async (question: Question) => {
    await shareMutation.mutateAsync({
      id: question.id,
      share: !question.share_with_physician,
    });
  };

  const handleStartEdit = (question: Question) => {
    setEditingId(question.id);
    setEditText(question.question_text);
  };

  const handleSaveEdit = async (id: string) => {
    if (!editText.trim()) return;

    await updateMutation.mutateAsync({
      id,
      question_text: editText.trim(),
    });

    setEditingId(null);
    setEditText('');
  };

  const handleDelete = async (id: string) => {
    if (window.confirm('Are you sure you want to delete this question?')) {
      await deleteMutation.mutateAsync(id);
    }
  };

  const handleMarkAnswered = async (question: Question) => {
    await updateMutation.mutateAsync({
      id: question.id,
      is_answered: !question.is_answered,
    });
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const getCategoryLabel = (category: string) => {
    const labels: Record<string, string> = {
      symptom: 'Symptom',
      medication: 'Medication',
      treatment: 'Treatment',
      other: 'Other',
    };
    return labels[category] || category;
  };

  return (
    <QuestionsPageContainer>
      <PageHeader>
        <h1>
          <MessageCircleQuestion size={28} />
          Questions to Ask Doctor
        </h1>
        <p>
          Write down questions you'd like to discuss with your care team. 
          Share them to make them visible in your doctor's portal.
        </p>
      </PageHeader>

      {/* New Question Form */}
      <QuestionForm onSubmit={handleSubmit}>
        <QuestionInput
          placeholder="Type your question here... (e.g., 'Should I take my anti-nausea medication before or after meals?')"
          value={newQuestion}
          onChange={(e) => setNewQuestion(e.target.value)}
          maxLength={2000}
        />
        
        <div className="form-actions">
          <div className="form-row">
            <CategorySelect
              value={newCategory}
              onChange={(e) => setNewCategory(e.target.value as typeof newCategory)}
            >
              <option value="symptom">Symptom Related</option>
              <option value="medication">Medication</option>
              <option value="treatment">Treatment</option>
              <option value="other">Other</option>
            </CategorySelect>

            <ShareToggle>
              <input
                type="checkbox"
                checked={shareNew}
                onChange={(e) => setShareNew(e.target.checked)}
              />
              <span className="share-label">
                <Share2 size={16} />
                Share with doctor
              </span>
            </ShareToggle>
          </div>

          <SubmitButton 
            type="submit" 
            disabled={!newQuestion.trim() || createMutation.isPending}
          >
            <Plus size={18} />
            {createMutation.isPending ? 'Adding...' : 'Add Question'}
          </SubmitButton>
        </div>
      </QuestionForm>

      {/* Filter Tabs */}
      <FilterTabs>
        <FilterTab $active={filter === 'all'} onClick={() => setFilter('all')}>
          All ({data?.questions.length || 0})
        </FilterTab>
        <FilterTab $active={filter === 'shared'} onClick={() => setFilter('shared')}>
          <Eye size={14} style={{ marginRight: 4 }} />
          Shared
        </FilterTab>
        <FilterTab $active={filter === 'private'} onClick={() => setFilter('private')}>
          <EyeOff size={14} style={{ marginRight: 4 }} />
          Private
        </FilterTab>
        <FilterTab $active={filter === 'answered'} onClick={() => setFilter('answered')}>
          <CheckCircle size={14} style={{ marginRight: 4 }} />
          Answered
        </FilterTab>
      </FilterTabs>

      {/* Questions List */}
      {isLoading ? (
        <LoadingSpinner>
          <div className="spinner" />
        </LoadingSpinner>
      ) : filteredQuestions.length === 0 ? (
        <EmptyState>
          <MessageCircleQuestion className="icon" />
          <h3>No questions yet</h3>
          <p>
            {filter === 'all' 
              ? "Write down questions you'd like to ask your doctor."
              : `No ${filter} questions found.`}
          </p>
        </EmptyState>
      ) : (
        <QuestionsList>
          {filteredQuestions.map((question) => (
            <QuestionCard 
              key={question.id}
              $shared={question.share_with_physician}
              $answered={question.is_answered}
            >
              <div className="question-header">
                <div className="question-meta">
                  <Badge $variant="category">
                    {getCategoryLabel(question.category)}
                  </Badge>
                  {question.share_with_physician && (
                    <Badge $variant="shared">
                      <Eye size={12} />
                      Shared with Doctor
                    </Badge>
                  )}
                  {question.is_answered && (
                    <Badge $variant="answered">
                      <CheckCircle size={12} />
                      Answered
                    </Badge>
                  )}
                </div>
              </div>

              {editingId === question.id ? (
                <div style={{ marginBottom: 16 }}>
                  <QuestionInput
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    style={{ minHeight: 80 }}
                  />
                  <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                    <ActionButton 
                      $variant="share"
                      onClick={() => handleSaveEdit(question.id)}
                      disabled={updateMutation.isPending}
                    >
                      <Send size={14} />
                      Save
                    </ActionButton>
                    <ActionButton onClick={() => setEditingId(null)}>
                      Cancel
                    </ActionButton>
                  </div>
                </div>
              ) : (
                <p className="question-text">{question.question_text}</p>
              )}

              <div className="question-footer">
                <span className="question-date">
                  <Clock size={14} style={{ marginRight: 4, verticalAlign: 'middle' }} />
                  {formatDate(question.created_at)}
                </span>

                <div className="question-actions">
                  <ActionButton
                    $variant="share"
                    onClick={() => handleToggleShare(question)}
                    disabled={shareMutation.isPending}
                    title={question.share_with_physician ? 'Make Private' : 'Share with Doctor'}
                  >
                    {question.share_with_physician ? <EyeOff size={14} /> : <Share2 size={14} />}
                    {question.share_with_physician ? 'Unshare' : 'Share'}
                  </ActionButton>

                  <ActionButton
                    $variant="mark"
                    onClick={() => handleMarkAnswered(question)}
                    disabled={updateMutation.isPending}
                  >
                    <CheckCircle size={14} />
                    {question.is_answered ? 'Reopen' : 'Mark Answered'}
                  </ActionButton>

                  <ActionButton
                    $variant="edit"
                    onClick={() => handleStartEdit(question)}
                    disabled={editingId !== null}
                  >
                    <Edit3 size={14} />
                  </ActionButton>

                  <ActionButton
                    $variant="delete"
                    onClick={() => handleDelete(question.id)}
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 size={14} />
                  </ActionButton>
                </div>
              </div>
            </QuestionCard>
          ))}
        </QuestionsList>
      )}
    </QuestionsPageContainer>
  );
};

export default QuestionsPage;

