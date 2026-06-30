/**
 * 聊天输入区组件
 * 处理问题输入、发送和停止当前流式请求
 */
import { ArrowUp, Square, WandSparkles } from "lucide-react";
import React, { FormEvent, KeyboardEvent, useRef } from "react";
import { cn } from "../lib/format";

type ComposerProps = {
    value: string;
    disabled: boolean;
    isStreaming: boolean;
    onChange: (value: string) => void;
    onSubmit: () => void;
    onStop: () => void;
};

export const Composer = React.memo(function Composer({ value, disabled, isStreaming, onChange, onSubmit, onStop }: ComposerProps) {
    const textareaRef = useRef<HTMLTextAreaElement | null>(null);

    const submit = (event: FormEvent) => {
        event.preventDefault();
        if (!disabled) onSubmit();
    };

    const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            if (!disabled) onSubmit();
        }
    };

    return (
        <form onSubmit={submit} className="border-t border-gray-200 bg-white/80 px-4 py-4 backdrop-blur">
            <div className="mx-auto flex max-w-5xl items-end gap-3 rounded-xl border border-gray-200 bg-white p-2 shadow-elevated">
                <div className="hidden h-11 w-11 shrink-0 place-items-center bg-patina/10 text-patina sm:grid">
                    <WandSparkles className="h-5 w-5" aria-hidden="true" />
                </div>
                <textarea
                    ref={textareaRef}
                    value={value}
                    onChange={(event) => onChange(event.target.value)}
                    onKeyDown={onKeyDown}
                    rows={1}
                    placeholder="输入你的问题..."
                    aria-label="输入问题"
                    className="max-h-36 min-h-11 flex-1 resize-none bg-transparent px-2 py-3 text-[15px] leading-6 text-gray-900 outline-none placeholder:text-gray-300"
                />
                <button
                    type={isStreaming ? "button" : "submit"}
                    onClick={isStreaming ? onStop : undefined}
                    disabled={!isStreaming && disabled}
                    className={cn(
                        "grid h-11 w-11 shrink-0 place-items-center rounded-full text-white transition focus:outline-none focus:ring-2 focus:ring-kinpaku/40 focus:ring-offset-2",
                        isStreaming
                            ? "bg-red-500 hover:bg-red-600"
                            : "bg-lacquer hover:bg-lacquer-light disabled:cursor-not-allowed disabled:bg-gray-300",
                    )}
                    title={isStreaming ? "停止" : "发送"}
                    aria-label={isStreaming ? "停止" : "发送"}
                >
                    {isStreaming ? (
                        <Square className="h-4 w-4 fill-current" aria-hidden="true" />
                    ) : (
                        <ArrowUp className="h-5 w-5" aria-hidden="true" />
                    )}
                </button>
            </div>
        </form>
    );
});
