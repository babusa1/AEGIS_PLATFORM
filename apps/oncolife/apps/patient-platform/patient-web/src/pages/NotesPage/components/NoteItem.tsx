import React from 'react';
import { Button } from 'react-bootstrap';
import { Trash2 } from 'lucide-react';
import { NoteItemContainer, NoteTitle, NotePreview } from './NoteItem.styles';
import type { Note } from '../types';

interface NoteItemProps {
  note: Note;
  isSelected: boolean;
  onSelect: () => void;
  onDelete?: (noteId: string) => void;
}

export const NoteItem: React.FC<NoteItemProps> = ({ note, isSelected, onSelect, onDelete }) => {
  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete && onDelete(note.id || '');
  };

  return (
    <NoteItemContainer 
      isSelected={isSelected}
      onClick={onSelect}
      style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <NoteTitle>{note.title}</NoteTitle>
        <NotePreview>{note.diary_entry}</NotePreview>
      </div>
      <Button
        variant="outline-danger"
        size="sm"
        onClick={handleDelete}
        style={{
          padding: '0.375rem',
          border: 'none',
          backgroundColor: 'transparent',
          color: '#dc3545',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minWidth: 'auto',
          marginLeft: '0.5rem',
          transition: 'all 0.2s ease'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = '#dc3545';
          e.currentTarget.style.color = 'white';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'transparent';
          e.currentTarget.style.color = '#dc3545';
        }}
      >
        <Trash2 size={16} />
      </Button>
    </NoteItemContainer>
  );
}; 