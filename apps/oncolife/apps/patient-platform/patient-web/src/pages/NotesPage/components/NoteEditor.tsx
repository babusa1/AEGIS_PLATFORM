import React, { useState, useCallback } from 'react';
import { EditorContainer, EditorHeader, EditorContent, EditorHeading, SaveButton, DeleteButton, CancelButton, EditorInput, EditorTextarea } from './NoteEditor.styles';
import type { Note } from '../types';

interface NoteEditorProps {
  note: Note;
  onNoteUpdate: (note: Note) => void;
  onSaveNote: (note: Note) => void;
  onDeleteNote: (noteId: string) => void;
  isDraft?: boolean;
  onCancelDraft?: () => void;
}

export const NoteEditor: React.FC<NoteEditorProps> = ({ note, onNoteUpdate, onSaveNote, onDeleteNote, isDraft, onCancelDraft }) => {
  const [title, setTitle] = useState(note.title);
  const [content, setContent] = useState(note.diary_entry);
  const [isEditing, setIsEditing] = useState(false);

  const titleInputRef = useCallback((node: HTMLInputElement | null) => {
    if (node && isEditing && lastEditField === 'title') {
      node.focus();
    }
  }, [isEditing]);

  const contentTextareaRef = useCallback((node: HTMLTextAreaElement | null) => {
    if (node && isEditing && lastEditField === 'content') {
      node.focus();
    }
  }, [isEditing]);

  const [lastEditField, setLastEditField] = useState<'title' | 'content' | null>(null);

  const handleTitleClick = () => {
    setIsEditing(true);
    setLastEditField('title');
  };

  const handleContentClick = () => {
    setIsEditing(true);
    setLastEditField('content');
  };

  const handleSave = () => {
    const updatedNote: Note = {
      ...note,
      title,
      diary_entry: content,
      // preview: content.substring(0, 50) + (content.length > 50 ? '...' : '')
    };
    onNoteUpdate(updatedNote);
    
    if (!note.id) {
      onSaveNote(updatedNote);
    }
    
    setIsEditing(false);
  };

  const handleCancel = () => {
    if (isDraft && onCancelDraft) {
      onCancelDraft();
    } else {
      setTitle(note.title);
      setContent(note.diary_entry);
      setIsEditing(false);
    }
  };

  const handleTitleChange = (newTitle: string) => {
    setTitle(newTitle);
  };

  const handleContentChange = (newContent: string) => {
    setContent(newContent);
  };

  return (
    <EditorContainer>
      <EditorHeader>
        {isEditing ? (
          <>
            <EditorHeading>
              <EditorInput
                type="text"
                value={title}
                onChange={(e) => handleTitleChange(e.target.value)}
                ref={titleInputRef}
                placeholder="Title"
                autoFocus
              />
            </EditorHeading>
          </>
        ) : (
          <EditorHeading onClick={handleTitleClick} style={{ cursor: 'pointer', width: '100%' }}>
            <EditorInput
              type="text"
              value={title}
              readOnly
              style={{ background: '#f8f9fa', cursor: 'pointer' }}
            />
          </EditorHeading>
        )}
      </EditorHeader>

      <EditorContent>
        {isEditing ? (
          <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <EditorTextarea
              value={content}
              onChange={(e) => handleContentChange(e.target.value)}
              placeholder="Start writing your note..."
              ref={contentTextareaRef}
              autoFocus={lastEditField === 'content'}
            />
          </div>
        ) : (
          <div onClick={handleContentClick} style={{ cursor: 'pointer', height: '100%' }}>
            <EditorTextarea
              value={content || 'Click to start writing...'}
              readOnly
              style={{ background: '#f8f9fa', cursor: 'pointer', minHeight: 200 }}
            />
          </div>
        )}
      </EditorContent>
      {isEditing && (
        <div style={{ 
          position: 'absolute', 
          bottom: '2rem', 
          right: '2rem', 
          zIndex: 1000,
          display: 'flex',
          gap: '1rem'
        }}>
          <CancelButton
            onClick={handleCancel}
          >
            Cancel
          </CancelButton>
          {!isDraft && (
            <DeleteButton
              onClick={() => onDeleteNote && onDeleteNote(note.id || '')}
            >
              Delete
            </DeleteButton>
          )}
          <SaveButton
            onClick={handleSave}
          >
            Save
          </SaveButton>
        </div>
      )}
    </EditorContainer>
  );
}; 